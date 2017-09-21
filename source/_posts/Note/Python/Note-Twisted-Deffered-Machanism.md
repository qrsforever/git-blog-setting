---

title: 笔记-Twisted的Deffered机制
date: 2017-09-01 16:41:00
tags: [Python, Twisted]
categories: [Note]

---

```

reactor --> Linux
              |
              |
              v
class EPollReactor(posixbase.PosixReactorBase, posixbase._PollLikeMixin):
                                    △
                                    |
           +------------------------+                                                          _newTimedCalls
           |                                                                                       /  ^
class PosixReactorBase(_SignalReactorMixin, _DisconnectSelectableMixin, ReactorBase):             /   |
                                ^                                           △                    /    |
                                |                                           |                   /     | 存放
              +-----------------+                         +-----------------+                  /      |
              |                                           |                    /---------------       |
class _SignalReactorMixin(object):              class ReactorBase(object):    /                       |
           |                                            |                pack a callable obj          |
           |                                            |--> callLater()  -----------------> class DelayedCall:
           |                                            |                                       /     |
         1 +--> run()                                   |                                      /      |
           |                                            |--> fireSystemEvent("startup")       /       |
           |                                            |       start threadpool             /        |
         2 +--> startRunning()  --->  startRunning() <--+                                   /         +--> getTime()
           |                                            |                          --------/          |
           |                                            |                         /                   +--> active*()
         3 +--> mainLoop()                              |                        /                    |
           |       |          +--- runUntilCurrent() <--+  run times call ------/                     +--> delay()
           |       |          |                         |                                             |
           |       | mix call |                         |                                             +--> __le__(), __lt__()
           |       +--------->|----------- timeout() <--+  determine the sleep time                   |  (when push order by time)
                              |                         |                                             |
                              |                         |
                              +---     doIteration() <--+
                                            |           |
                                            | impl
                                            v
                                   EPollReactor.doPoll()
                                    poll(timeout, fds)


```
mainLoop()是由几层while嵌套实现以poll机制驱动整个程序运作.
<!-- more -->

----

# Twisted介绍

## Deffereds
Twisted uses the Deferred object to manage the callback sequence. The client application attaches a series of functions to the
deferred to be called in order when the results of the asynchronous request are available (this series of functions is known as a
    series of callbacks, or a callback chain), together with a series of functions to be called if there is an error in the
asynchronous request (known as a series of errbacks or an errback chain). The asynchronous library code calls the first callback
when the result is available, or the first errback when an error occurs, and the Deferred object then hands the results of each
callback or errback function to the next function in the chain.

[引用](https://twistedmatrix.com/documents/current/core/howto/defer.html)

## Callback
A twisted.internet.defer.Deferred is a promise that a function will at some point have a result. We can attach callback functions
to a Deferred, and once it gets a result these callbacks will be called. In addition Deferreds allow the developer to register a
callback for an error, with the default behavior of logging the error. The deferred mechanism standardizes the application
programmer’s interface with all sorts of blocking or delayed operations.

## Timeouts
Timeouts are a special case of Cancellation. Let’s say we have a Deferred representing a task that may take a long time. We want
to put an upper bound on that task, so we want the Deferred to time out X seconds in the future.
A convenient API to do so is Deferred.addTimeout. By default, it will fail with a TimeoutError if the Deferred hasn’t fired (with
either an errback or a callback) within timeout seconds.

# 源码实例
## 代码-1 (单回调)

```

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from twisted.internet import reactor, defer

def getDummyData(inputData):
    print('getDummyData called')
    deferred = defer.Deferred()
    reactor.callLater(2, deferred.callback, inputData * 3)
    return deferred

def cbPrintData(result):
    print('Result received: {}'.format(result))

deferred = getDummyData(3)
deferred.addCallback(cbPrintData)

# manually set up the end of the process by asking the reactor to
# stop itself in 4 seconds time
reactor.callLater(4, reactor.stop)
# start up the Twisted reactor (event loop handler) manually
print('Starting the reactor')
reactor.run()

```
如果reactor.callLater(2, deferred.callback, inputData * 3)参数deferred.callback换成普通函数, 那么deferred.addCallback添加的
callback将不会执行, 要理解DelayCall对象和Deffered中callbacks之间的联系. [Deffered类](#deff_c "Deffered简易图")
如果有多个deferred.addCallback, 前一个回调的返回作为后一个callback的参数.


## 代码-2 (多回调)

```

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from twisted.internet import reactor, defer

class Getter:
    def gotResults(self, x):
        if self.d is None:
            print("Nowhere to put results")
            return

        d = self.d
        self.d = None
        if x % 2 == 0:
            d.callback(x*3)
        else:
            d.errback(ValueError("You used an odd number!"))

    def _toHTML(self, r):
        return "Result: %s" % r

    def getDummyData(self, x):
        self.d = defer.Deferred()
        reactor.callLater(2, self.gotResults, x)
        self.d.addCallback(self._toHTML)
        return self.d

def cbPrintData(result):
    print(result)

def ebPrintError(failure):
    import sys
    sys.stderr.write(str(failure))

# this series of callbacks and errbacks will print an error message
g = Getter()
d = g.getDummyData(3)
d.addCallback(cbPrintData)
d.addErrback(ebPrintError)

# this series of callbacks and errbacks will print "Result: 12"
g = Getter()
d = g.getDummyData(4)
d.addCallback(cbPrintData)
d.addErrback(ebPrintError)

reactor.callLater(4, reactor.stop)
reactor.run()

```

## 代码-3 (线程)

```

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from twisted.internet.defer import Deferred
from twisted.internet import reactor

import threading

def loadRemoteData(callback, errback, url):
    print("thread[%s] url = %s" % (threading.current_thread().name, url))
    # callback 和 errback 只能调用其中一个,  否则:AlreadyCalledError
    callback('callback data')
    #  errback(ValueError("errback dat"))

def getResult(v):
    print("thread[%s] result = %s" % (threading.current_thread().name, v))

def getError(e):
    print("thread[%s] error = %s" % (threading.current_thread().name, str(e)))

if __name__ == '__main__':
    d = Deferred()
    d.addCallback(getResult)
    d.addErrback(getError)

    print("main():thread[%s]" % threading.current_thread().name)
    reactor.callInThread(loadRemoteData, d.callback, d.errback, "http://www.baidu.com")
    reactor.callLater(4, reactor.stop);
    reactor.run()

```

# 源码剖析

主要文件:
1. defer.py
2. base.py

## Deffered类

<span id="deff_c"></span>

```

class Deferred
        |          callbacks: 存callback, _chainedTo: 将多个Deffered串成链                     reactor.callLater
        |                                                                                              |
        +---> addCallbacks() <---+----+----+                                                           |
        |                        |    |    |                                                           |
        +---> addCallback() -----+    |    | call                                                      v
        |                             |    |                                                       DelayedCall
        +---> addErrback() -----------+    |                                                           |
        |                                  |                                                           |
        +---> addBoth() -----------+-------+                                                           |
        |                          |                                                                   v
        +---> addTimeout() --------+                                                              reactor.run
        |                                                                                              |
        +---> pause()/cancel()                                                                         |
        |                                                                                              |
        |                             Understand the relation between callback and DelayCall           v
        +---> callback() ---------    <----------------------------------------------------+        timeout
        |                call   /                                                          |           |
        +---> errback()-----   /                                                           |           |
        |                 /   /                                                            |           |
        |                /   /                                                             |           v
        |               v   v                                                 DelayedCall.fun()-->Deferred.callback()
        +--->  _runCallbacks                                                                           |
        |              |                                                                               |
        |              o----> item = callbacks.pop(0)                                                  |
        |              |                                                                               |
        |              | Normal:                                                                       |
        |              o----> item.callbak()    <------------------------------------------------------+
        |              |
        |              | Exception:
        |              o----> failure.Failure()
        |              |

```


## reactor方法

### 1. reactor.callLater()

```

// reactor.callLater(2, deferred.callback, inputData * 3)

@implementer(IReactorCore, IReactorTime, IReactorPluggableResolver,
             IReactorPluggableNameResolver)
class ReactorBase(object):
    ...
    def callLater(self, _seconds, _f, *args, **kw):
       tple = DelayedCall(self.seconds() + _seconds, _f, args, kw,
                          self._cancelCallLater,
                          self._moveCallLaterSooner,
                          seconds=self.seconds)
       self._newTimedCalls.append(tple)
       return tple

```

将参数封装到DelayedCall对象中并存储在\_newTimeCalls变量中, 需要注意的是callLater处理及回调函数还是在主线程中调用的.

### 2. reactor.run()

```

// reactor.run()
class _SignalReactorMixin(object):
    ...
    def run(self, installSignalHandlers=True):
        self.startRunning(installSignalHandlers=installSignalHandlers)
        self.mainLoop()


    def startRunning(self, installSignalHandlers=True):
        self._installSignalHandlers = installSignalHandlers
        ReactorBase.startRunning(self)


    def mainLoop(self):
        while self._started:
            try:
                while self._started:
                    self.runUntilCurrent()
                    t2 = self.timeout()
                    t = self.running and t2
                    self.doIteration(t)
            except:
                log.msg("Unexpected error in main loop.")
                log.err()
            else:
                log.msg('Main loop terminated.')


```

\_SignalReactorMixi 混合类, 调用了与它自身没有任何血缘关ReactorBase的方法*runUntilCurrent*, *timeout*, *doIteration*及*startRunning*.


```

class ReactorBase(object):
           |
           |
           +---> startRunning()
           |      |
           |      |
           |      |
           +------o---> fireSystemEvent()
           |                 |              "startup"
           |                 |
           |                 o---> _eventTriggers.get()
           |                 |
           |                 |
           |                 o---> event.fireEvent()
           |                 |            | running = True
           |                              |
           |                              o---> DeferredList.addCallback()
           +---> mainLoop()               |                      |
           |        |                                            |
           |        |                                            o---> Deferred._runCallbacks()
           |        o---> runUntilCurrent()                      |
           |        |
           |                 _pendingTimedCalls
           |                   队列中以时间排序
           |


```

reactor在install初始化时完成了两个重要操作:
1. self.\_initThreads() 线程池
2. self.installWaker()  唤醒线程, impl: PosixReactorBase.installWaker


```

class ReactorBase(object):
    ...
    def runUntilCurrent(self):
        """
        Run all pending timed calls.
        """
        if self.threadCallQueue:
            count = 0
            total = len(self.threadCallQueue)
            for (f, a, kw) in self.threadCallQueue:
                try:
                    f(*a, **kw)
                except:
                    log.err()
                count += 1
                if count == total:
                    break
            del self.threadCallQueue[:count]
            if self.threadCallQueue:
                self.wakeUp()

        # insert new delayed calls now
        self._insertNewDelayedCalls()

        now = self.seconds()
        while self._pendingTimedCalls and (self._pendingTimedCalls[0].time <= now):
            call = heappop(self._pendingTimedCalls)
            if call.cancelled:
                self._cancellations-=1
                continue

            if call.delayed_time > 0:
                call.activate_delay()
                heappush(self._pendingTimedCalls, call)
                continue

            try:
                call.called = 1
                call.func(*call.args, **call.kw)
            except:
                ...


        if (self._cancellations > 50 and
             self._cancellations > len(self._pendingTimedCalls) >> 1):
            self._cancellations = 0
            self._pendingTimedCalls = [x for x in self._pendingTimedCalls
                                       if not x.cancelled]
            heapify(self._pendingTimedCalls)

        if self._justStopped:
            self._justStopped = False
            self.fireSystemEvent("shutdown")

```

### 3. reactor.callInThread()

涉及文件:

文件 | 路径 |
------- | :----------------
base.py          |   /usr/local/lib/python3.4/dist-packages/twisted/internet
defer.py         |   /usr/local/lib/python3.4/dist-packages/twisted/internet
threadpool.py    |   /usr/local/lib/python3.4/dist-packages/twisted/python
context.py       |   /usr/local/lib/python3.4/dist-packages/twisted/python
_pool.py         |   /usr/local/lib/python3.4/dist-packages/twisted/_threads
_team.py         |   /usr/local/lib/python3.4/dist-packages/twisted/_threads
_threadworker.py |   /usr/local/lib/python3.4/dist-packages/twisted/_threads


**context.py模块中call/get方法代理:**

```

def installContextTracker(ctr):
    global theContextTracker
    global call
    global get

    theContextTracker = ctr
    call = theContextTracker.callWithContext
    get = theContextTracker.getContext

installContextTracker(ThreadedContextTracker())


```


**func函数线程调用图:**

```

ReactorBase    Deferred      ThreadPool    ContextTracker      Team        LockWorker      ThreadWorker      LocalStorage
  |                             |                 |              |             |               |                   |
  | callInThread                |                 |              |             |               |                   |
  +---------------------------->|callInThread     |              |             |               |                   |
  |                      func   |    |            |              |             |               |                   |
  |                                  |            |     inContext|             |               |                   |
  |                      callInThreadWithCallback--------------->|do           |               |                   |
  |                                  |            |              |             |               |                   |
  |                                  |            |              |             |               |                   |
  |                                  |            |              +------------>|do             |                   |
                                     |            |              |        work |               |                   |
                                     |            |              |             |               |            append |
                                     |            |              |             |---------------------------------->|working
                                     |            |              |             |               |                   |
                                     |            |              |                             |             pop   |
                                     |            |              |<------------------------------------------------|
    +----------------------+         |            |      _coordinateThisTask                   |
    |  _coordinateThisTask |         |            |                 |        _pool.py          |
    |                      |         |            |                 |            |             |
    |   +--------------+   |         |            |          worker |------------------------->| __init__
    |   |    doWork    |   |         |            |                 |    limitedWorkerCreator  |     |
    |   | +----------+ |   |         |            |                 |            |             |     |
    |   | | inContext| |   |         |            |                 |            |             |     |
    |   | |  +----+  | |   |         |            |                 |       startThread <------------|
    |   | |  |func|  | |   |         |            |                 |            |             |     |
    |   | |  +----+  | |   |         |            |                 |            |             |     |
    |   | +----------+ |   |         |            |                 |     Thread.start()------------>| work()
    |   +--------------+   |         |            |                 |                          |          |
    +----------------------+         |            |                 |                          |    while | get task
                                     |            |       @worker.do|                          |          |<------<
                                     |            |                 |------------------------->|do        |       |
                                     |            |                 |                          |          |       |
                                     |            |                 |                          | put task |       |
                                     |            |                 |                          |--------> |       |
                                     |            |                 |                          |          |       |
                                     |            |                 |                                     |       |
                                     |            |          doWork |<------------------------------ task()-------^
                                     |            |            |    |                                     |
                                     |            |            |    |                                     |
                                  inContext<--------task() <---+    |                                   <===> thread end!
                                      |           |                 |
                                      | theWork() |                 | _recycleWorker
                                      |---------->| context.call    |
                                                         |
                                                         |
                                                         |
                                                   callWithContext
                                                         |
                                                         |
              func() <-----------------------------------+

```

**过程**: 初始化线程池ThreadPool --> 线程协调LockWorker --> 创建工作线程ThreadWorker --> 传递任务(team.do) --> 线程中处理任务 --> 回收
线程

**原理**: ThreadWorker维护Queue将传递过来的task加入队列, ThreadWorker在初始化时调用startThread()启动Thread.start, 到此一个新的
线程被创建, 该新线程会执行ThreadWorker中work方法, work方法从Queue队列中取新的task去执行.
