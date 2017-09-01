---
title: 笔记-Twisted的Deffered机制
date: 2017-09-01 16:41
tags: [Python, Twisted]
categories: [笔记]

---

## Reactor类图和调用关系

```
reactor --> Linux
              |
              |
              v
class EPollReactor(posixbase.PosixReactorBase, posixbase._PollLikeMixin):
                                    ^
                                    |
           +------------------------+
           |
class PosixReactorBase(_SignalReactorMixin, _DisconnectSelectableMixin, ReactorBase):
                                ^                                           ^
                                |                                           |
              +-----------------+                         +-----------------+
              |                                           |
class _SignalReactorMixin(object):              class ReactorBase(object):
           |                                            |                pack a callable obj
           |                                            |--> callLater()  -----------------> class DelayedCall:
           |                                            |                                             |
         1 +--> run()                                   |                                             |
           |                                            |--> fireSystemEvent("startup")               |
           |                                            |       start threadpool                      |
         2 +--> startRunning()  --->  startRunning() <--+                                             +--> getTime()
           |                                            |                                             |
           |                                            |                                             +--> active*()
         3 +--> mainLoop()                              |                                             |
           |       |          +--- runUntilCurrent() <--+  run times call                             +--> delay()
           |       |          |                         |                                             |
           |       | mix call |                         |                                             +--> __le__(), __lt__()
           |       +--------->|----------- timeout() <--+  determine the sleep time                   |  (when push order by time)
                              |                         |                                             |
                              |                         |
                              +---     doIteration() <--+
                                                        |

```

\_SignalReactorMixi 混合类, 里面调用了与它自身没有任何血缘关系的方法*runUntilCurrent*, *timeout*, *doIteration*以及*startRunning*.

<!-- more -->












