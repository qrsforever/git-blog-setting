---

title: Hadoop之Delete实例代理流程
date: 2017-11-13 18:57:00
tags: [ Hadoop, Java ]
categories: [ Note ]

---

```
              ClientNamenodeProtocol
                     |
                     |
                     o---> newReflectiveBlockingService  -----> BlockingService
                     |                                                |
                     |                                                |
                     o---> newBlockingStub                            o--> getDescriptorForType()
                     |        |                                       |
                     |        |new                                    o--> getRequestPrototype()
                     |        |                                       |
                     |        +----> BlockingStub                     o--> getResponsePrototype()
                     |                   △                            |
                     |                   |                            o--> callBlockingMethod()
                     |                   |                            |        |
                     |            BlockingInterface                   |        |
                     |                |  △                            |        o--> impl.delete()
                     |                |  |
                     |                |  |
                     |     delete <-- o  |
                     |                |  +---------------------------------------+
                                                                                 |
                                                                                 |
                                                                                 |
                 ClientProtocol        +----------------------------> ClientNamenodeProtocolPB
                      △                |                                         △
                      |                |rpcProxy                                 |
                      |                |                                         |
                      |                ◆                                         |
         ClientNamenodeProtocolTranslatorPB                  ClientNamenodeProtocolServerSideTranslatorPB
               (Client Proxy)                                               (Server Impl)
                      |                                                          |
                      | 1                                                   5    |
                      o---> delete()                                delete() <---o
                      |        |                                       ^         |
                      |        |  2                                    |         |
                               o---> rpcProxy.delete()                 |
                                                |                      |
                                                |                      |
                               +----------------+                 +----+
                               |                                  |
    +----------------          |                                  |                    -----------------+
    |                          |                                  |                                     |
    |                          |                                  |                                     |
    |   RpcInvocationHandler   |                                  |                RPC.Server           |
    |              e1          |                                  |                e1                   |
    |               \          |                                  |               /                     |
    |                \         |                                  |              /                      |
    |                 \        |                                  |             /                       |
    |                Invoker   |                                  |       Server                        |
    |                  |       |                                  |        |                            |
    |                  |   3   v                                  |   4    |                            |
    |                  o---> invoke()                           call() <---o                            |
    |                  |                                                   |                            |
    |                  |                                                   |                            |
    |                                                                                                   |
    +---------------------------------------------------------------------------------------------------+
                                              ProtobufRpcEngine
```
