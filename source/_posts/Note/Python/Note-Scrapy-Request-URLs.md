---

title: Scrapy之Requst URLs处理流程
date: 2017-09-20 20:49:41
tags: [Python, Scrapy, Crawler]
categories: [ 笔记 ]

---

<span id="global-uml"></span>
```
                                                                         scrapy.utils.defer.process_chain()
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
                                                   o--->  _process_chain()            |
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
                                      o---> process_start_requests(start_requests)
                                      |             /
                                      |            /
                                      |   +-------------------------------------------------------------------------------------+
                                      |   |   def process_start_requests(self, start_requests, spider):    ★2                   |
                                      |   |       return self._process_chain('process_start_requests', start_requests, spider)  |
                                                                  --------------------------------------------------------------+

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

Scrapy中大量使用Twisted中的延迟机制, [参考前文](http://www.lanrenflower.com/2017/09/11/Note/Python/Note-Twisted-InlineCallback)
self.spider: 命令行参数指定的spider,如s51job对应的类S51jobSpider
self.engine: 调度执行spider, 驱动spider前行
self.start_requests(): 调用基类的的实现, 方法中使用了yield是个生成器方法, 把start_urls封装城Request对象中

```
                                                                            +---------------------------------------------------+
    S51jobSpider ------▷  CrawlSpider -----▷  Spider                     ---| def start_requests(self):                         |
                                                |    start_urls         /   |     ...                                           |
                                                |                      /    |        for url in self.start_urls:                |
                                                -----> start_requests()     |            yield Request(url, dont_filter=True)   |
                                                |                           +---------------------------------------------------+
                                                |

```

# 源码open_spider()
core.engine.ExecutionEngine.open_spider():

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

start_requests: 作为参数时是Spider.start_requests()生成器方法, yield返回变为process_start_requests()生成器方法
self.crawler: 初始化时传过来的scrapy.crawler.Crawler, 启动爬虫对象
scheduler: scrapy.core.scheduler.Scheduler, 对优先级, Memory, Disk队列push/pop调度管理
scrape.spidermw: Core.Scraper.SpiderMiddlewareManager
[start_requests流程图](#global-uml)
