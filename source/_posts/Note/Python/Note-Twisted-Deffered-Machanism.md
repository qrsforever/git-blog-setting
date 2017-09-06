---
title: 笔记-Twisted的Deffered机制
date: 2017-09-01 16:41:00
tags: [Python, Twisted]
categories: [笔记]

---

# Twisted 介绍

## Deffereds
Twisted uses the Deferred object to manage the callback sequence. The client application attaches a series of functions to the
deferred to be called in order when the results of the asynchronous request are available (this series of functions is known as a
    series of callbacks, or a callback chain), together with a series of functions to be called if there is an error in the
asynchronous request (known as a series of errbacks or an errback chain). The asynchronous library code calls the first callback
when the result is available, or the first errback when an error occurs, and the Deferred object then hands the results of each
callback or errback function to the next function in the chain.

[引用](https://twistedmatrix.com/documents/current/core/howto/defer.html)

<!-- more -->

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

### 代码实例-1 (单回调)

```
#!/usr/bin/python3
# -*- coding: utf-8 -*-

from twisted.internet import reactor, defer

def getDummyData(inputData):
    """
    This function is a dummy which simulates a delayed result and
    returns a Deferred which will fire with that result. Don't try too
    hard to understand this.
    """
    print('getDummyData called')
    deferred = defer.Deferred()
    # simulate a delayed result by asking the reactor to fire the
    # Deferred in 2 seconds time with the result inputData * 3
    reactor.callLater(2, deferred.callback, inputData * 3)
    return deferred

def cbPrintData(result):
    """
    Data handling function to be added as a callback: handles the
    data by printing the result
    """
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

### 代码实例-2 (多回调)

```

#!/usr/bin/python3
# -*- coding: utf-8 -*-

from twisted.internet import reactor, defer

class Getter:
    def gotResults(self, x):
        """
        The Deferred mechanism provides a mechanism to signal error
        conditions.  In this case, odd numbers are bad.

        This function demonstrates a more complex way of starting
        the callback chain by checking for expected results and
        choosing whether to fire the callback or errback chain
        """
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
        """
        This function converts r to HTML.

        It is added to the callback chain by getDummyData in
        order to demonstrate how a callback passes its own result
        to the next callback
        """
        return "Result: %s" % r

    def getDummyData(self, x):
        """
        The Deferred mechanism allows for chained callbacks.
        In this example, the output of gotResults is first
        passed through _toHTML on its way to printData.

        Again this function is a dummy, simulating a delayed result
        using callLater, rather than using a real asynchronous
        setup.
        """
        self.d = defer.Deferred()
        # simulate a delayed result by asking the reactor to schedule
        # gotResults in 2 seconds time
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

# 源码剖析

## Deffered类

```

class Deferred
        |          callbacks: 存callback, _chainedTo: 将多个Deffered串成链
        |
        +---> addCallbacks() <---+----+----+
        |                        |    |    |
        +---> addCallback() -----+    | 都 |
        |                             | 调 |
        +---> addErrback() -----------+ 用 |
        |                                  |
        +---> addBoth() -----------+-------+
        |                          |
        +---> addTimeout() --------+
        |
        +---> pause()/cancel()
        |
        |
        +---> callback() ---------
        |                       /
        +---> errback()-----   / 调用
        |                 /   /
        |                /   /
        |               v   v
        +--->  _runCallbacks
        |              |
        |              o----> item = callbacks.pop(0)
        |              |
        |              |正常:
        |              o----> item.callbak()
        |              |
        |              |异常:
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
       """See twisted.internet.interfaces.IReactorTime.callLater.
       """
       tple = DelayedCall(self.seconds() + _seconds, _f, args, kw,
                          self._cancelCallLater,
                          self._moveCallLaterSooner,
                          seconds=self.seconds)
       self._newTimedCalls.append(tple)
       return tple

```

将参数2, deferred.callback函数引用等参数封装到DelayedCall对象中并存储在\_newTimeCalls变量中.

### 2. reactor.run()

```

// reactor.run()
class _SignalReactorMixin(object):
    ...
    def run(self, installSignalHandlers=True):
        self.startRunning(installSignalHandlers=installSignalHandlers)
        self.mainLoop()


    def startRunning(self, installSignalHandlers=True):
        """
        Extend the base implementation in order to remember whether signal
        handlers should be installed later.

        @type installSignalHandlers: C{bool}
        @param installSignalHandlers: A flag which, if set, indicates that
            handlers for a number of (implementation-defined) signals should be
            installed during startup.
        """
        self._installSignalHandlers = installSignalHandlers
        ReactorBase.startRunning(self)


    def mainLoop(self):
        while self._started:
            try:
                while self._started:
                    # Advance simulation time in delayed event
                    # processors.
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
           |                 |              running = True
           |
           |
           +---> mainLoop()
           |        |
           |        |                              _pendingTimedCalls
           |        o---> runUntilCurrent()         队列中以时间排序
           |        |
           |
           |
           |


```

reactor在install初始化时完成了两个重要操作:
> 1. self.\_initThreads()  线程池
> 2. self.installWaker()  唤醒线程, impl: PosixReactorBase.installWaker


```

class ReactorBase(object):
    ...
    def runUntilCurrent(self):
        """
        Run all pending timed calls.
        """
        if self.threadCallQueue:
            # Keep track of how many calls we actually make, as we're
            # making them, in case another call is added to the queue
            # while we're in this loop.
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
                log.deferr()
                if hasattr(call, "creator"):
                    e = "\n"
                    e += " C: previous exception occurred in " + \
                         "a DelayedCall created here:\n"
                    e += " C:"
                    e += "".join(call.creator).rstrip().replace("\n","\n C:")
                    e += "\n"
                    log.msg(e)


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

## 类图和调用关系

```

reactor --> Linux
              |
              |
              v
class EPollReactor(posixbase.PosixReactorBase, posixbase._PollLikeMixin):
                                    ^
                                    |
           +------------------------+                                                          _newTimedCalls
           |                                                                                       /  ^
class PosixReactorBase(_SignalReactorMixin, _DisconnectSelectableMixin, ReactorBase):             /   |
                                ^                                           ^                    /    |
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
                                        not impl        |

```
