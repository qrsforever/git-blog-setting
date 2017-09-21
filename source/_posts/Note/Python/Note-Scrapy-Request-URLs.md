---

title: Scrapy之Requst URLs处理流程
date: 2017-09-20 20:49:41
tags: [Python, Scrapy, Crawler]
categories: [ Note ]

---

<span id="global-uml"></span>
```
                                                                             ★0
   start_requests = yield self.scraper.spidermw.process_start_requests(start_requests, spider)
          |
          |generator                          +----------------------------------------------------------------------------+
          |                                   |                                                                            |
          |                                   |  def _runCallbacks(self):                                                  |
          |                                   |      ...                                                                   |
          |                                   |      while current.callbacks:                                              |
          |                                   |          item = current.callbacks.pop(0)                                   |
          |                                   |          callback, args, kw = item[                                        |
          |                                   |              isinstance(current.result, failure.Failure)]                  |
          |                                   |          ...                                                               |
          |             current.result        |              try:                                                          |
          +--------------------+-------------------------------- current.result = callback(current.result, *args, **kw)    |
                               |              |              ...                                                           |
                               |              |              else:                                                         |
                               |              |                  if isinstance(current.result, Deferred):                  |
                               |              |                      ...                                                   |
                               |              +----------------------------------------------------------------------------+
                               |                                                                              ^
                               |                                                                              |
                               |                                                                              | d.callback(input)
                               |                                                                              |
                               | generator                                                                    |
                               v                                         scrapy.utils.defer.process_chain()   |
Crawl51JobSpiderMiddleware.process_start_requests()                      +------------------------------------------------+
 +------------------------------------------------------------+          |                                ★4              |
 |                                          ★5                |          |  def process_chain(callbacks, input, *a, **kw):|
 |  def process_start_requests(self, start_requests, spider): |      x   |      d = defer.Deferred()                      |
 |      for r in start_requests:                              | <-------------  for x in callbacks:                       |
 |          yield r                                           |          |          d.addCallback(x, *a, **kw)            |
 +------------------------------------------------------------+          |      d.callback(input)                         |
                                                                         |      return d                                  |
                                                                         +------------------------------------------------+
                                                                                      |
                                                   |                                  |
                                                   m ---> _process_chain()            |
                                                   |              \                   |
                                                   |               \                  |
                                                   |        +-----------------------------------------------------------------+
                              MiddlewareManager ---+        |  def _process_chain(self, methodname, obj, *args):  ★3          |
                                      △            |        |      return process_chain(self.methods[methodname], obj, *args) |
                                      |            |        +-----------------------------------+-----------------------------+
                                      |            |                                            |
                                      |            |                                            |
                                      |            |                                            |
                                      |            |                                            v
                                      |                                   Crawl51JobSpiderMiddleware.process_start_requests()
                 spidermw             |
        Scraper ◆---------> SpiderMiddlewareManager
                                      |
                                      |                                ★1
                                      m---> process_start_requests(start_requests)
                                      |             /
                                      |            /
                                      |   +-------------------------------------------------------------------------------------+
                                      |   |   def process_start_requests(self, start_requests, spider):    ★2                   |
                                      |   |       return self._process_chain('process_start_requests', start_requests, spider)  |
                                      |   +-------------------------------------------------------------------------------------+

```

<!-- more -->

> 命令启动crawl
scrapy crawl --nolog  s51job -o /tmp/file.csv

# 源码crawl()

crawler.Crawler.crawl():

```

    @defer.inlineCallbacks
    def crawl(self, *args, **kwargs):
        self.crawling = True
        try:
            self.spider = self._create_spider(*args, **kwargs)
            self.engine = self._create_engine()
            start_requests = iter(self.spider.start_requests())
            yield self.engine.open_spider(self.spider, start_requests)
            yield defer.maybeDeferred(self.engine.start)
        ...

```

Scrapy中大量使用Twisted中的延迟机制 [参考前文](http://www.lanrenflower.com/2017/09/11/Note/Python/Note-Twisted-InlineCallback)
self.spider: 命令行参数指定的spider,如s51job对应的类S51jobSpider
self.engine: 调度执行spider, 驱动spider前行
self.start\_requests(): 调用基类的的实现, 方法中使用了yield是个生成器方法, 把start\_urls封装城Request对象中

```
                                                                            +---------------------------------------------------+
    S51jobSpider ------▷  CrawlSpider -----▷  Spider                     ---| def start_requests(self):                         |
                                                |    start_urls         /   |     ...                                           |
                                                |                      /    |        for url in self.start_urls:                |
                                                m----> start_requests()     |            yield Request(url, dont_filter=True)   |
                                                |                           +---------------------------------------------------+
                                                |

```

# 源码open_spider()
core.engine.ExecutionEngine.open\_spider():

```

    @defer.inlineCallbacks
    def open_spider(self, spider, start_requests=(), close_if_idle=True):
        ...
        nextcall = CallLaterOnce(self._next_request, spider)
        scheduler = self.scheduler_cls.from_crawler(self.crawler)
        start_requests = yield self.scraper.spidermw.process_start_requests(start_requests, spider)
        slot = Slot(start_requests, close_if_idle, nextcall, scheduler)
        self.slot = slot
        self.spider = spider
        yield scheduler.open(spider)
        yield self.scraper.open_spider(spider)
        self.crawler.stats.open_spider(spider)
        yield self.signals.send_catch_log_deferred(signals.spider_opened, spider=spider)
        slot.nextcall.schedule()
        slot.heartbeat.start(5)

```

start\_requests: 作为参数时是Spider.start\_requests()生成器方法, yield返回变为process\_start\_requests()生成器方法
self.crawler: 初始化时传过来的scrapy.crawler.Crawler, 启动爬虫对象
scheduler: scrapy.core.scheduler.Scheduler, 对优先级, Memory, Disk队列push/pop调度管理
scrape.spidermw: Core.Scraper.SpiderMiddlewareManager
slot.nextcall: 实现\_\_call\_\_()方法的[CallLaterOnce](#src_calllater)类, 该类()调用的是\_next\_request()
slot.heartbeat: twisted.internet.task.[LoopingCall](#src_loopcall)(nextcall.schedule)

[start\_requests流程图](#global-uml)


# 源码CallLaterOnce()

<span id="src_calllater"></span>

```

class CallLaterOnce(object):
    def __init__(self, func, *a, **kw):
        self._func = func
        self._a = a
        self._kw = kw
        self._call = None

    def schedule(self, delay=0):
        if self._call is None:
            self._call = reactor.callLater(delay, self)

    def cancel(self):
        if self._call:
            self._call.cancel()

    def __call__(self):
        self._call = None
        return self._func(*self._a, **self._kw)

```

self.\_func(): \_next\_request()
callLater(): 将self(可执行的类)封装到DelayedCall()并加入到以delay时间排序的队列中, 等待执行. [了解更多](
    http://www.lanrenflower.com/2017/09/01/Note/Python/Note-Twisted-Deffered-Machanism/)
call: nextcall.schedule() --> reactor.callLater() --> \_next\_request()

# 源码LoopingCall()

```
class LoopingCall:
    call = None
    running = False
    _deferred = None
    interval = None
    _runAtStart = False
    starttime = None

    def __init__(self, f, *a, **kw):
        self.f = f
        self.a = a
        self.kw = kw
        from twisted.internet import reactor
        self.clock = reactor

    def start(self, interval, now=True):
        self.running = True
        deferred = self._deferred = defer.Deferred()
        self.starttime = self.clock.seconds()
        self.interval = interval
        self._runAtStart = now
        if now:
            self()
        else:
            self._scheduleFrom(self.starttime)
        return deferred

    def stop(self):
        self.running = False
        if self.call is not None:
            self.call.cancel()
            self.call = None
            d, self._deferred = self._deferred, None
            d.callback(self)
    ...

    def __call__(self):
        def cb(result):
            if self.running:
                self._scheduleFrom(self.clock.seconds())
            else:
                d, self._deferred = self._deferred, None
                d.callback(self)

        def eb(failure):
            self.running = False
            d, self._deferred = self._deferred, None
            d.errback(failure)

        self.call = None
        d = defer.maybeDeferred(self.f, *self.a, **self.kw)
        d.addCallback(cb)
        d.addErrback(eb)

    ...

    def _scheduleFrom(self, when):
        def howLong():
            if self.interval == 0:
                return 0
            runningFor = when - self.starttime
            untilNextInterval = self.interval - (runningFor % self.interval)
            if when == when + untilNextInterval:
                return self.interval
            return untilNextInterval
        self.call = self.clock.callLater(howLong(), self)

```

self.f: nextcall.schedule():
seconds(): 返回当前系统时间秒数(根据平台不同, 实现不同)
start(): 启动loop任务, 以interval为循环周期, 执行\_\_call\_\_()
\_\_call\_\_(): 调用maybeDeferred()执行self.f 即nextcall.schedule()该函数返回值为None.

# 源码maybeDeferred()

```

def succeed(result):
    d = Deferred()
    d.callback(result)
    return d

def fail(result=None):
    d = Deferred()
    d.errback(result)
    return d

def maybeDeferred(f, *args, **kw):

    try:
        result = f(*args, **kw)
    except:
        return fail(failure.Failure(captureVars=Deferred.debug))

    if isinstance(result, Deferred):
        return result
    elif isinstance(result, failure.Failure):
        return fail(result)
    else:
        return succeed(result)

```

f(): == nextcall.shedule(), 返回值为None, 所以maybeDeferred()此处返回succeed(result), callback回调执行LoopingCall\_\_call\_\_.cb()

URL调度:

```


                               |
                               m---> _scheduleFrom()  <-----------------------------------------+
                               |          |                                                     |
                               |          |                                                     |
                               |          o---> reactor.callLater(interval, self)               | loop-2
                               |                                                                |
                               m---> start(interval)                                            |
                               |       |                                                        |
                               |       |                                                        |
             LoopingCall ------+       o---> self()--+                                          |
                 ^             |                     |                                          |
                 |             |                     |    +-----> self._scheduleFrom(interval)--+
                 |             m---> __call__()  <---+    |
                 |             |        |                 |
                 |                      |                 |           +----> errback()
                 |                      |        cb-------+           |
                 |                      |        eb-------------------+
                 |                      o --->  defer.maybeDeferred(self.f)
     heartbeat   |                      |                                | is
                 ◆     nextcall                                          |
                Slot ◆-----------> CallLaterOnce                         |
                 ◆                      |                                |
                 |                      |         ★1                     |
                 |                      m ---> schedule()  <-------------+---------------+
                 |                      |           |                                    |
                 v                      |           |                                    |
             start_requests             |           o ---> reactor.callLater(0, self)    |
                                        |           |                  |                 |
                                        |                     call     |                 |
                                        m ---> __call__()  <-----------+                 |
                                        |         |                                      |
                                        |         |             ★2                       |
                                                  o ---> self._func()                    |
                   |                              |             |                        |
                   |           ★3                               |                        |
                   m ---> _next_request()  <--------------------+ is                     |
                   |            |                                                        |
                   |      call  |                                                        |
 ExecutionEngine --+        +---o                                                        |
                   |        |   |                                                        |
                   |        |   |       ★4                                               |
                   |        |   o---> request = next(slot.start_requests)                |
                   |        |   |                                                        |
                   |        |   |  call                                                  |
   download() <--- m        |   o-------------------------------+                        |
                   |        |   |                               |                        |
                   |        |                                   |                        |
                   |        |                                   |                        |
                   |        |                                   |                        | loop-1
                   |        v       ★8                          |                        |
                   m ---> _next_request_from_scheduler()        |                        |
                   |        |                                   |                        |
                   |        |                       ★9          |                        |
                   |        o---> slot.scheduler.next_request() |                        |
                   |        |                                   |                        |
                   |        |              ★10                  |                        |
                   |        o---> self._download()              |                        |
                   |        |                                   |                        |
                   |                                            |                        |
                   m ---> crawl()  <----------------------------+                        |
                   |        |                                                            |
                   |        |            ★5                                              |
                   |        o---> self.schedule()                                        |
                   |        |           |                                                |
                   |        |           |                          ★6                    |
                   |        |           o---> slot.scheduler.enqueue_request()           |
                            |                                                            |
                            o---> self.slot.nextcall.schedule() -------------------------+
                            |                         ★7
                            |

```

# 疑问: 

在open\_spider函数的最后两行代码:
>  slot.nextcall.schedule()
>  slot.heartbeat.start(5)

分析源码之后发现这两行的动作有些重复, nextcall.schedule()自身也能实现loop, 如上图(Loop-1), heartbeat.start(5)(Loop-2)是不是多余的?
这个疑问留到以后解决
