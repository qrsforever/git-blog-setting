---

title: Scrapy之命令行启动流程
date: 2017-08-31 16:01:00
tags: [Python, Scrapy, Crawler]
categories: [Note]

---

```


                     +------------------------------>  Settings  <-------------------------------------------------+
                     |                                    |                       settings.py                      |
                     ◆                                    | extend           +-------------------+                 |
               ScrapyCommand                              ▽                  | SPIDER_MIDDLEWARES|                 |
                △      |                              BaseSettings           | ITEM_PIPELINES    |                 |
                |      |                                  |                  | SPIDER_MODULES    |                 |
                |      o---> add_options()                |                  +-------------------+                 |
                |      |                                  o---> setmodule()         |                              |
                |      |                                  |            |            |                              |
             Command   o---> process_options()            |            |------------+                              |
                |      |                                  o---> set <--|                                           |
                |      |                                  |            =                                           |
                |      o---> virtual run()                |                                                        |
                |                                                                                                  |
         crawl  o---> run()                                                                                        |
           |    |      |                                     command:                                              |
           |    |      |  ★                     1           +-------------------------------------------------+    |
           |    =      +---> crawler_process.crawl()        |                                                 |    |
           |           |                                    | scrapy crawl --nolog s51job -o /tmp/result.csv  |    |
           |           |                        5           |                                                 |    |
           |           +---> crawler_process.start()        +-------------------------------------------------+    |
           |           |                                                                                           |
           |                                                                                                       |
           |                            extend                               crawlers 1:n                          |
           o----> CrawlerProcess -----------------------▷  CrawlerRunner  ◆----------------------->  Crawler ◇-----+
           |            |                                        |                  s51job         /   |
           |            |                                        |           2                    /    | ★
                        o---> start()                            o---> create_crawler()          /     o---> crawl() <--------+
                        |        |                               |           |                  /      |                      |
                        |        |                               |           |                 /       |                      |
                        |        +---> reactor.getThreadPool()   |           +----------------/        o---> _create_spider   |
                        |        |                               |                     |               |                      |
                        |        |                               |                     |               |                      |
                        |        +---> reactor.run()             |                     +------+        o---> _create_engine() |
                        |        |                               o---> stop()                 |        |                      |
                        |        =                               |                            |        =                      |
                        |                                        |                            |                               |
                        o---> _stop_reactor                      o---> join()                SpiderLoader                     |
                        |                                        |                                |                           |
                        =                                        |       4                        |                           |
                                                                 o---> crawl()                    o---> _load_all_spiders()   |
                                                                 |       |                        |                           |
               Spider ◁----- CrawlSpider ◁----- S51jobSpider     |       |                        |         3                 |
                   |          |                          \       =       +---> crawler.crawl()    o---> load(name)            |
                   |          |                           \              |                |       |                           |
    start_urls <---o          o---> rules                  \                              |       =                           |
                   |          |                             \  is                         |                                   |
                   |          |                              ------- _create_spider() <---+ spider                            |
       parse() <---o          o---> parse_start_url()                                     |                              <----+
                   |          |                                    6                      |
                   |          =                                      _create_engine() <---+ engine
                   |                                              /                       |
                   o---> start_requests()                     is /                        |
                   |       yield ☜                              /                         =
                   =                       ExecutionEngine -----
                                              ◆     |
                                              |     | ★           7
                                              |     o---> open_spider()              +------------------+
                                              |     |                                |                  |
        Slot <--------------------------------+     |                                |                  |
         |                                          o---> start()                    |  Twisted Deffer  |
         |                                          |                                |                  |
         o---> nextcall()                           |                                |                  |
         |                                          o---> stop/pause/close()         +------------------+
         |                                          |
         o---> scheduler()                          |
         |                                          o---> download/schedule/crawl()
         |        8                                 |
         o---> heartbeat()-----------+              |
         |      |                    |              o---> _next_request()
         =      | task.LoopingCall() |              |
                +--------------------+              =

```

<!-- more -->


## Scrapy 命令启动
### scrapy crawl 执行流程
**bin/scrapy**:
```python
 7 from scrapy.cmdline import execute
 8
 9 if __name__ == '__main__':
10     sys.argv[0] = re.sub(r'(-script\.pyw|\.exe)?$', '', sys.argv[0])
11     sys.exit(execute())
```

**scrapy/cmdline.py**:
```python
 97 def execute(argv=None, settings=None):
 98     if argv is None:
 99         argv = sys.argv
100
101     # --- backwards compatibility for scrapy.conf.settings singleton ---
102     if settings is None and 'scrapy.conf' in sys.modules:
103         from scrapy import conf
104         if hasattr(conf, 'settings'):
105             settings = conf.settings
106     # ------------------------------------------------------------------
107
108     if settings is None:
109         settings = get_project_settings()
110         # set EDITOR from environment if available
111         try:
112             editor = os.environ['EDITOR']
113         except KeyError: pass
114         else:
115             settings['EDITOR'] = editor
116     check_deprecated_settings(settings)
117
118     # --- backwards compatibility for scrapy.conf.settings singleton ---
119     import warnings
120     from scrapy.exceptions import ScrapyDeprecationWarning
121     with warnings.catch_warnings():
122         warnings.simplefilter("ignore", ScrapyDeprecationWarning)
123         from scrapy import conf
124         conf.settings = settings
125     # ------------------------------------------------------------------
126
127     inproject = inside_project()
128     cmds = _get_commands_dict(settings, inproject)
129     cmdname = _pop_command_name(argv)
130     parser = optparse.OptionParser(formatter=optparse.TitledHelpFormatter(), \
131         conflict_handler='resolve')
132     if not cmdname:
133         _print_commands(settings, inproject)
134         sys.exit(0)
135     elif cmdname not in cmds:
136         _print_unknown_command(settings, cmdname, inproject)
137         sys.exit(2)
138
139     cmd = cmds[cmdname]
140     parser.usage = "scrapy %s %s" % (cmdname, cmd.syntax())
141     parser.description = cmd.long_desc()
142     settings.setdict(cmd.default_settings, priority='command')
143     cmd.settings = settings
144     cmd.add_options(parser)
145     opts, args = parser.parse_args(args=argv[1:])
146     _run_print_help(parser, cmd.process_options, args, opts)
147
148     cmd.crawler_process = CrawlerProcess(settings)
149     _run_print_help(parser, _run_command, cmd, args, opts)
150     sys.exit(cmd.exitcode)
151
152 def _run_command(cmd, args, opts):
153     if opts.profile:
154         _run_command_profiled(cmd, args, opts)
155     else:
156         cmd.run(args, opts)
```
前大部分对参数和工程Setting解析处理, 最后_run_print\_help -->\_run\_command --> cmd.run, 这里的cmd实际上就是crawl

**commands/crawl.py**:
```python
50     def run(self, args, opts):
51         if len(args) < 1:
52             raise UsageError()
53         elif len(args) > 1:
54             raise UsageError("running 'scrapy crawl' with more than one spider is no longer supported")
55         spname = args[0]
56
57         self.crawler_process.crawl(spname, **opts.spargs)
58         self.crawler_process.start()
```
继续调用crawler\_process对象中crawl,start方法, 即CrawlerProcess, 其父类CrawlerRunner实现crawl方法

**crawler.py**:
```
110 class CrawlerRunner(object):
144     def crawl(self, crawler_or_spidercls, *args, **kwargs):
166         crawler = self.create_crawler(crawler_or_spidercls)
167         return self._crawl(crawler, *args, **kwargs)
181     def create_crawler(self, crawler_or_spidercls):
192         if isinstance(crawler_or_spidercls, Crawler):
193             return crawler_or_spidercls
194         return self._create_crawler(crawler_or_spidercls)
195
196     def _create_crawler(self, spidercls):
197         if isinstance(spidercls, six.string_types):
198             spidercls = self.spider_loader.load(spidercls)
199         return Crawler(spidercls, self.settings)
```
crawler\_or\_spidercls spider名字, 经过spider\_loader.load()转换为对应的spider对象(父类CrawlSpider), 这一步很关键, 自己实现的spider 继承CrawlSpider.
self.spider\_loader: scrapy.spiderloader.SpiderLoader

**spiderloader.py**:
```
15 class SpiderLoader(object):
16     """
17     SpiderLoader is a class which locates and loads spiders
18     in a Scrapy project.
19     """
20     def __init__(self, settings):
21         self.spider_modules = settings.getlist('SPIDER_MODULES')
22         self.warn_only = settings.getbool('SPIDER_LOADER_WARN_ONLY')
23         self._spiders = {}
24         self._found = defaultdict(list)
25         self._load_all_spiders()
    ...
44     def _load_all_spiders(self):
45         for name in self.spider_modules:
47                 for module in walk_modules(name):
48                     self._load_spiders(module)
```
SPIDER\_MODULES: 当前工程settings.py变量
_load_all\_spiders: 加载所有自定义的spider


**crawler.py**:
```
27 class Crawler(object):
28
70     def crawl(self, *args, **kwargs):
71         assert not self.crawling, "Crawling already taking place"
72         self.crawling = True
73
74         try:
75             self.spider = self._create_spider(*args, **kwargs)
76             self.engine = self._create_engine()
77             start_requests = iter(self.spider.start_requests())
78             yield self.engine.open_spider(self.spider, start_requests)
79             yield defer.maybeDeferred(self.engine.start)
80         except Exception:
89             self.crawling = False
90             if self.engine is not None:
91                 yield self.engine.close()
92
93             if six.PY2:
94                 six.reraise(*exc_info)
95             raise

97     def _create_spider(self, *args, **kwargs):
98         return self.spidercls.from_crawler(self, *args, **kwargs)
```

self.spidercls.from\_crawler调入到CrawlSpider

**spiders/crawl.py**:
```
 34 class CrawlSpider(Spider):
 35
 98     @classmethod
 99     def from_crawler(cls, crawler, *args, **kwargs):
100         spider = super(CrawlSpider, cls).from_crawler(crawler, *args, **kwargs)
101         spider._follow_links = crawler.settings.getbool(
102             'CRAWLSPIDER_FOLLOW_LINKS', True)
103         return spider
```

**spiders/__init__.py**:
```
18 class Spider(object_ref):
49     @classmethod
50     def from_crawler(cls, crawler, *args, **kwargs):
51         spider = cls(*args, **kwargs)
52         spider._set_crawler(crawler)
53         return spider

```
到此应该知道自己的spider 如何创建的了

### Crawler, Spider和Engine

**scrapy/crawler.py**:
```
 27 class Crawler(object):
     ...
 70     def crawl(self, *args, **kwargs):
 71         assert not self.crawling, "Crawling already taking place"
 72         self.crawling = True
 73
 74         try:
 75             self.spider = self._create_spider(*args, **kwargs)
 76             self.engine = self._create_engine()
    ...
 97     def _create_spider(self, *args, **kwargs):
 98         return self.spidercls.from_crawler(self, *args, **kwargs)
 99
100     def _create_engine(self):
101         return ExecutionEngine(self, lambda _: self.stop())

```

ExecutionEngine 结构:
```
▼ ExecutionEngine : class
   +__init__ : function
   +start : function
   +stop : function
   +close : function
   +pause : function
   +unpause : function
   +_next_request : function
   +_needs_backout : function
   +_next_request_from_scheduler : function
   +_handle_downloader_output : function
   +spider_is_idle : function
   +open_spiders : function
   +has_capacity : function
   +crawl : function
   +schedule : function
   +download : function
   +_downloaded : function
  ▼+_download : function
     +_on_success : function
     +_on_complete : function
   +open_spider : function
   +_spider_idle : function
  ▼+close_spider : function
    ▼+log_failure : function
       +errback : function
   +_close_all_spiders : function
   +_finish_stopping_engine : function
```

**core/engine.py**:
```
 56 class ExecutionEngine(object):
 57
 58     def __init__(self, crawler, spider_closed_callback):
 59         self.crawler = crawler
 60         self.settings = crawler.settings
 61         self.signals = crawler.signals
 62         self.logformatter = crawler.logformatter
 63         self.slot = None
 64         self.spider = None
 65         self.running = False
 66         self.paused = False
 67         self.scheduler_cls = load_object(self.settings['SCHEDULER'])
 68         downloader_cls = load_object(self.settings['DOWNLOADER'])
 69         self.downloader = downloader_cls(crawler)
 70         self.scraper = Scraper(crawler)
 71         self._spider_closed_callback = spider_closed_callback
    ...
253     def open_spider(self, spider, start_requests=(), close_if_idle=True):
254         assert self.has_capacity(), "No free spider slot when opening %r" % \
255             spider.name
256         logger.info("Spider opened", extra={'spider': spider})
257         nextcall = CallLaterOnce(self._next_request, spider)
258         scheduler = self.scheduler_cls.from_crawler(self.crawler)
259         start_requests = yield self.scraper.spidermw.process_start_requests(start_requests, spider)
260         slot = Slot(start_requests, close_if_idle, nextcall, scheduler)
261         self.slot = slot
262         self.spider = spider
263         yield scheduler.open(spider)
264         yield self.scraper.open_spider(spider)
265         self.crawler.stats.open_spider(spider)
266         yield self.signals.send_catch_log_deferred(signals.spider_opened, spider=spider)
267         slot.nextcall.schedule()
268         slot.heartbeat.start(5)

```

**Setting**

name | value
----- | -----
SCHEDULER | scrapy.core.scheduler.Scheduler
DOWNLOADER | scrapy.core.downloader.Downloader
DUPEFILTER_CLASS | scrapy.dupefilters.RFPDupeFilter
SCHEDULER_PRIORITY_QUEUE | queuelib.PriorityQueue
SCHEDULER_DISK_QUEUE | scrapy.squeues.PickleLifoDiskQueue
SCHEDULER_MEMORY_QUEUE | scrapy.squeues.LifoMemoryQueue
SPIDER_LOADER_CLASS | scrapy.spiderloader.SpiderLoader
