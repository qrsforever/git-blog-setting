---

title: Twisted InlineCallback 机制
date: 2017-09-11 15:06:16
tags: [ Twisted, Python ]
categories: [ Note ]

---

<span id="code-flow"></span>
```
                                                d0.addCallback()
 +----------------------------------------------------------------------------------------------------------------------+
 |                                                                                                                      |
 |                                                (g)                                                                   v
 |    main      inlineCallbacks              getRemoteData          loadRemoteData          loadRemoteData2         getResult
 |     |              |     \                      |                        |                      |                    |
 |     |              |      \inner                |                        |                      |                    |
 |     |              |       \                    |                        |                      |                    |
 |     |------------->|        \                   |                        |                      |                    |
 |     |              |       gotResult            |                        |                      |                    |
 |     |              |d0         |                |                        |                      |                    |
 |     |              |           |   g.send(None) |                        |                      |                    |
 |     |              |--------------------------->|                        |                      |                    |
 |     |              |           |                |                        |                      |                    |
 |     |              |           |                |d1                      |                      |                    |
 +-- d0|<-------------|           |                |                        |                      |                    |
       |              |           |return is deffer|---callInThread         |                      |                    |
       |        ----d1|<---------------------------|        |               |                      |                    |
       |       /                 -|                |        |               |                      |                    |
       |      /       |         / |                |        |               |                      |                    |
       |    addBoth() |        /  |                | Thread |-------------->|                      |                    |
       |       |      |       /   |                |        |               |                      |                    |
       |       +--------------    |  r = 1         |                        | callback(1)          |                    |
       |              |           |<----------------------------------------|                      |                    |
       |              |  r = 1    |                |                        =                      |                    |
       |              |<----------|                |                                               |                    |
       |              |           |                |                                               |                    |
       |              |           |    g.send(1)   |                                               |                    |
       |              |--------------------------->|r1 = 1                                         |                    |
       |              |           |                |                                               |                    |
       |              |           |                |d2                                             |                    |
       |              |           |                |                                               |                    |
       |              |           |return is deffer|--callInThread                                 |                    |
       |        ----d2|<---------------------------|        |                                      |                    |
       |       /      |           |                |        |                                      |                    |
       |      /       |           |                |        |                                      |                    |
       |    addBoth() |           |                | Thread |------------------------------------->|                    |
       |       |      |           |                |        |                                      |                    |
       |       +------|           |  r = 2         |                                               |callback(2)         |
       |              |           |<---------------------------------------------------------------|                    |
       |              |   r = 2   |                |                                               =                    |
       |              |<----------|                |                                                                    |
       |              |           |                |                                                                    |
       |              |                g.send(2)   |                                                                    |
       |              |--------------------------->|r2 = 2                                                              |
       |              |                            |                                                                    |
       |              |                            |--returnValue(r1+r2)                                                |
       |              |                            =        |                                                           |
       |              |  try.catch                          |                                                           |
       |              |<------------------------------------|raise e(3)                                                 |
       |              |                                                                                                 |
       |              |                                                                                                 |
       |              | d0.callback(3)                                                                                  |
       |              |------------------------------------------------------------------------------------------------>|
       |              =                                                                                                 |
       |                                                                                                                |
       |                                                                                                         3 <----|output
       |                                                                                                                =
       =

```
<!-- more -->
[此图对应源码](#demo-code)

----

# Deferred的callback和addCallbacks方法

## addCallbacks()

```

    def addCallbacks(self, callback, errback=None,
                     callbackArgs=None, callbackKeywords=None,
                     errbackArgs=None, errbackKeywords=None):
        cbs = ((callback, callbackArgs, callbackKeywords),
               (errback or (passthru), errbackArgs, errbackKeywords))
        self.callbacks.append(cbs)

        if self.called:
            self._runCallbacks()
        return self

```

## callback()

```

    def callback(self, result):
        self._startRunCallbacks(result)

    def _startRunCallbacks(self, result):
        self.called = True
        self.result = result
        self._runCallbacks()

```

由 **self.called** 变量控制执行\_runCallbacks(), 默认为False, 只有调用callback之后才赋值True, 所以在没有调用callback之前调用
addCallBacks只是把cbs存放到self.callbacks变量中. 一般在调用callback之前会处理好需要的数据(eg: Request), 调用时把结果result作为
参数传给之前加进来的callbacks.


## runCallbacks()

```

  while current.callbacks:
      item = current.callbacks.pop(0)
      callback, args, kw = item[
          isinstance(current.result, failure.Failure)]
      args = args or ()
      kw = kw or {}
      ...
      try:
          current._runningCallbacks = True
          try:
              current.result = callback(current.result, *args, **kw)
              if current.result is current:
                ...
          finally:
              current._runningCallbacks = False
      except:
          current.result = failure.Failure(captureVars=self.debug)
      else:
          if isinstance(current.result, Deferred):
              resultResult = getattr(current.result, 'result', _NO_RESULT)
              if resultResult is _NO_RESULT or isinstance(resultResult, Deferred) or current.result.paused:
                  ...
                  break
              else:
                  # Yep, it did.  Steal it.
                  current.result.result = None
                  # Make sure _debugInfo's failure state is updated.
                  if current.result._debugInfo is not None:
                      current.result._debugInfo.failResult = None
                  current.result = resultResult

```

pop(0)始终弹出最早放进去的item(cb,eb), 也就是按addCallbacks的先入先出的顺序, 这个很关键, 以为前一个callback回调的返回是下一个
回调函数的输入.
>  current.result = callback(current.result, *args, **kw)


# InlineCallbacks 实例

## 实例源码
<span id="demo-code"></span>

```

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from twisted.internet import defer, reactor

def loadRemoteData(callback):
    print("---> loadRemoteData  callback: ", callback)
    import time
    time.sleep(1)
    callback(1) # 将1传给getResult, 只有callback之后才能触发callbacks结果

def loadRemoteData2(callback):
    print("---> loadRemoteData2 callback: ", callback)
    import time
    time.sleep(1)
    callback(2)

@defer.inlineCallbacks
def getRemoteData():
    d1 = defer.Deferred()
    # d1.callback 遍历回调所有callbacks
    reactor.callInThread(loadRemoteData, d1.callback)
    print("yiled d1: ", d1)
    r1 = yield d1
    d2 = defer.Deferred()
    reactor.callInThread(loadRemoteData2, d2.callback)
    print("yiled d2: ", d2)
    r2 = yield d2

    # 主动抛出_DefGen_Return异常, 异常的内容就是r1+r2
    defer.returnValue(r1+r2) # 函数中调用raise
    # 或者return导致抛StopIteration
    # return r1 + r2

def getResult(v):
    print ("result = ", v)

if __name__ == '__main__':
    d0 = getRemoteData()
    print("main d0 : ", d0)
    d0.addCallback(getResult)

    #  import time
    #  time.sleep(4)
    # 以下两行可以使用sleep替换, 不影响功能测试
    reactor.callLater(4, reactor.stop);
    reactor.run()

```

执行:
```

twisted$ ./inlineCallback.py
yiled d1:  <Deferred at 0x7f6b2a57fdd8>
main d0 :  <Deferred at 0x7f6b2a57fe10>
---> loadRemoteData  callback:  <bound method Deferred.callback of <Deferred at 0x7f6b2a57fdd8>>
yiled d2:  <Deferred at 0x7f6b25f75668>
---> loadRemoteData2 callback:  <bound method Deferred.callback of <Deferred at 0x7f6b25f75668>>
result =  3
twisted$

```

[代码流程图](#code-flow)

## 三个Deffered对象

对象名|对象地址|备注
:---:|:---:|:---
d0 | 0x7f6b2a57fe10 | 由@defer.inlineCallbacks内部创建, 且getResult回调持有者
d1 | 0x7f6b2a57fdd8 | 由getRemoteData函数创建, 被@defer.inlineCallbacks包装
d2 | 0x7f6b25f75668 | 同上

## getRemoteData()生成器

该函数中有yield调用, 则getRemoteData转变为生成器, 函数不会阻塞马上会返回, 而且被@defer.inlineCallbacks封装起来, 只有生成器函数
调用next()/send()方法才触发getRemoteData代码继续执行, 上面的实例并没有任何地方调用send/next, 程序是如何运行的? 还有通过d0的打印
来看d0的类型是Deffered对象而不是生成器函数? 带着这些疑问继续往下看.

# InlineCallbacks 源码分析

## 源码

```

def inlineCallbacks(f):
    @wraps(f)
    def unwindGenerator(*args, **kwargs):
        try:
            gen = f(*args, **kwargs)
        except _DefGen_Return:
            raise TypeError()
        if not isinstance(gen, types.GeneratorType):
            raise TypeError()
        return _inlineCallbacks(None, gen, Deferred())
    return unwindGenerator

def _inlineCallbacks(result, g, deferred):

    waiting = [True, # waiting for result?
               None] # result

    while 1:
        try:
            isFailure = isinstance(result, failure.Failure)
            if isFailure:
                result = result.throwExceptionIntoGenerator(g)
            else:
                result = g.send(result)
        except StopIteration as e:
            deferred.callback(getattr(e, "value", None))
            return deferred
        except _DefGen_Return as e:
            ...
            deferred.callback(e.value)
            return deferred
        except:
            deferred.errback()
            return deferred

        if isinstance(result, Deferred):
            def gotResult(r):
                if waiting[0]:
                    waiting[0] = False
                    waiting[1] = r
                else:
                    _inlineCallbacks(r, g, deferred)

            result.addBoth(gotResult)
            if waiting[0]:
                waiting[0] = False
                return deferred

            result = waiting[1]
            waiting[0] = True
            waiting[1] = None
    return deferred

class _DefGen_Return(BaseException):
    def __init__(self, value):
        self.value = value

def returnValue(val):
    raise _DefGen_Return(val)

```

g.send()返回如果是个Defferred, 需要对改Defferred注册cb,eb方法, 等待Defferred执行callbacks时会触发回调,并将结果传下来,再次调用
\_inlineCallbacks(), 如果g.send()返回是非Defferred对象, 则直接将该返回值作为g.send()的参数, 继续...

## @defer.inlineCallbacks 展开

```

def getRemoteData():
    d1 = defer.Deferred()
    # d1.callback 遍历回调所有callbacks
    reactor.callInThread(loadRemoteData, d1.callback)
    print("yiled d1: ", d1)
    r1 = yield d1
    d2 = defer.Deferred()
    reactor.callInThread(loadRemoteData2, d2.callback)
    print("yiled d2: ", d2)
    r2 = yield d2

    # 主动抛出_DefGen_Return异常, 异常的内容就是r1+r2
    defer.returnValue(r1+r2) # 函数中调用raise
    # 或者return导致抛StopIteration
    # return r1 + r2


def inlineCallbacks.unwindGenerator(*args, **kwargs):
    try:
        gen = getRemoteData(*args, **kwargs)
    except _DefGen_Return:
        raise TypeError()
    if not isinstance(gen, types.GeneratorType):
        raise TypeError()
    return _inlineCallbacks(None, gen, Deferred())

d0 = inlineCallbacks.unwindGenerator()


```

前面说过getRemoteData是个生成器, gen = getRemoteData(\*args, \*\*kwargs)这个调用会立即返回, 并作为参数传给\_inlineCallbacks, 猜测
生成器gen的next/send的调用应该发生再\_inlineCallbacks中.

## 揭开谜底

查看源码会发现**\_inlineCallbacks()**函数所有的return都是deferred变量, 这个变量是在InlineCallBacks的闭包函数里传入的Deffered(),实
际上这个值就是上层函数中的d0对象, d0对象在哪创建的疑问解决了; **\_inlineCallbacks()**里虽然有while 1循环, 但是调用它并不会使其阻塞
,原因就是return直接返回.

调用路线: result = g.send(result) --> if isinstance(result, Deferred) --> result.addBoth(gotResult) --> return deferred;

根据生成器规则(r = yield x), send的参数会传给r(第一次特殊None), 生成器函数返回x(=g.send()).
第一次send:
result = g.send(result), 此时参数result是None, 返回result是d1
result.addBoth(gotResult) == d1.addBoth(gotResult)
当某线程调用d1.callback()时, 会触发gotResult()函数调用, 并且d1.callback传入的参数1会传给gotResult(1), 又会触发\_inlineCallbacks().

第二次send:
result = g.send(result), 此时参数result就是1, 返回result是d2
result.addBoth(gotResult) == d2.addBoth(gotResult)
当某线程调用d2.callback()时, 会触发gotResult()函数调用, 并且d2.callback传入的参数2会传给gotResult(2), 又会触发\_inlineCallbacks().

第三次send:
result = g.send(result), 此时参数result就是2, getRemoteData()结束调用defer.returnValue(1+2), 触发异常\_DefGen\_Return().

捕捉异常, 获取异常值3
deferred.callback(e.value)
return deferred
