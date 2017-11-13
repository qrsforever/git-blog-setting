---

title: Hadoop之Namenode的Delete命令代码流程
date: 2017-11-10 21:01:00
tags: [ Hadoop, Java ]
categories: [ Note ]

---

```
                                                           nn
             +-------------------------------------------------+   +------------------------------------------------------------+
             |                                                 |   |                                                            |
             v       rpcServer                                 |   v                                                            |
        NameNode  ◇ -------------------------------------> NameNodeRpcServer ---------▷  NamenodeProtocols                      |
        ◇   |                                                ◆     |                               |       +-----------------+  |
        |   |  1                                             |     |                               |       |ClientProtocol   |  |
        |   o--> initialize()                serviceRpcServer|     o---> start()                   |       |DatanodeProtocol |  |
        |   |       |                                        |     |      |                        +-----▷ |NamenodeProtocol |  |
        |           |                         clientRpcServer|     |      |  3                             |HAServiceProtocol|  |
        |           o--> loadNamesystem()----\       ★       |     |      |--> clientRpcServer.start()     +-----------------+  |
        |           |                         \              |     |      |                                                     |
        |           o--> createRpcServer()     \             |     |      |--> serverRpcServer.start()                          |
        |           |                           \            |     |  13                                                        |
        |           o--> startCommonServices()   \           |     o---> delete()                                               |
        |           |        |                    \          |     |        |                                                   |
        |                    |  2                  \         |     |        |  14                                               |
        | namesystem         |--> rpcServer.start() \        |              o---> namesystem.delete()                           |
        |                    |                       |       |              |                                                   |
        |                                            |       |              |                                                   |
  FSNamesystem.loadFromDisk() <----------------------+       |                                                                  |
                                                             |                                                                  |
  +----------------------------------------------------------+                                                                  |
  |                                                                                                                             |
  | ipc.Server                                                                                                                  |
  |   △  |                                                                                                                      |
  |   |  |----------------------------------------------------------------------------------------                              |
  |   |  | Inner class       +-- Listener (listens on the socket, create jobs for handler threads)                              |
  |   |  |     |             |      | ◆                                                                                         |
  |   |  |     |             |      | |    readers                                                                              |
  |   |  |     v             |      | +------------------->  Reader()                                                           |
  |   |  |                   |      |                           |                                                               |
  |   |  |                   |      |                           o--> run()                                                      |
  |   |  |         Selector  |      o--> run():loop             |     |    readSelector.select()                                |
  |   |  |                   |      |     |   selector.select()       | 6                                                       |
  |   |  |                   |      |     | 5                         o---> doRead() +---------------->  Connection             |
  |   |  |              NIO  |            o---> doAccept()                     |     |                                          |
  |   |  |                   |                    |                            o---> c.readAndProcess()                         |
  |   |  |                   |                    |                            |            |   channelRead(ByteBuffer)         |
  |   |  |                   |                    o--> reader.addConnection(c)              |                                   |
  |   |  |                   |                                                              o--> processOneRpc()                |
  |   |  |                   |                                                              |         |                         |
  |   |  |                   |                                                                        | 7                       |
  |   |  |     Thread ◁ -----+-- Responder (sends responses of RPC back to clients)                   o--> processRpcRequest()  |
  |   |  |                   |       |                                                                            |             |
  |   |  |                   |       o--> run()                                                                   |             |
  |   |  |                   |       |                                                        Call(rpcRequest) <--o             |
  |   |  |                   |       |                                                              /                           |
  |   |  |              NIO  |       o--> doRunLoop()                                              /                            |
  |   |  |                   |       |                                                            /                             |
  |   |  |                   |                                                                   / callQueue.put(call)          |
  |   |  |                   |                                                                  /                               |
  |   |  |                   |                                                                 /                                |
  |   |  |                   |                                                                /                                 |
  |   |  |                   |                                                               /                                  |
  |   |  |                   +-- Handler (handles queued calls)                             /                                   |
  |   |  |                          |                                                      /                                    |
  |   |  |                          |                                                     /                                     |
  |   |  |                          o---> run():loop                                     /                                      |
  |   |  |                                 |                                     call   /                                       |
  |   |  |                                 |                                           /                                        |
  |   |  |                                 |---> callQueue.take() --------------------/                                         |
  |   |  |                                 |                                                                                    |
  |   |  |                                 |---> CurCall.set(call)                                                              |
  |   |  |                                 | 8                                                                                  |
  |   |  |                                 |---> call()                                                                         |
  |   |  |     ^                           |                                                                                    |
  |   |  |     |                           |---> CurCall.set(null)                                                              |
  |   |  |     |                                                                                                                |
  |   |  | Inner class                                                                                                          |
  |   |  |----------------------------------------------------------                                                            |
  |   |  |                                                                                                                      |
  |   |  o---> registerProtocolEngine()                                                                                         |
  |   |  |                                                                                                                      |
  |   |  o---> getRpcInvoker()                                                                                                  |
  |   |  |                                                                    RpcInvoker                                        |
  |   |  o---> call()         |--> responder.start()                                △                                           |
  |   |  |               4    |                                                     |                                           |
  |   |  o---> start() -------+--> listener.start()                                 o---> invoke()                              |
  |   |  |                    |                                                     |                                           |
  |   |                       |--> handler.start()                   ★              |                                           |
  v   |                                                      (clientRpcServer)      |                                           |
 RPC.Server ◁ ------------------------------------------ ProtobufRpcEngine.Server   |                                           |
      |                                                       |                     |                                           |
      |                                                       |---------------------|                                           |
      o---> addProtocol()                                     | Inner class         |                                           |
      |                                                       |   |                 |                                           |
      o---> registerProtocolAndImpl()                         |   |                 |                                           |
      |                                                       |   v          ProtoBufRpcInvoker                                 |
      | 8.1                                                   |              ^      |                                           |
      o---> call()                                            |             /       |                                           |
      |      |                                         +-------------------/        o---> getProtocolImpl()                     |
      |      |  rpcKind = RPC_PROTOCOL_BUFFER          |      |                     |                                           |
             |---> getRpcInvoker() --------------------+      |                     | 8.3                                       |
             |          |                                     |                     o---> call()                                |
                        | 8.2                                 |   ^                        |                                    |
                        |---> call()                          |   |                        |  9                                 |
                                                              |   |                        |--> service.callBlockingMethod()    |
                                                              | Inner class                |       |                            |
                                                              |---------------------               |                            |
                                                                                                   +--------------------------+ |
    ClientNamenodeProtocol.proto                                                                                              | |
    +--------------------------------------+                                                                                  | |
    |                                      |                                                       12 |                       | |
    |service  ClientNamenodeProtocol {     |                                        server.delete()<--o                       | |
    |  rpc delete(DeleteRequestProto)      |                                                          |                       | |
    |        returns(DeleteResponseProto); |                                                          |                       | |
    |}                                     |                                                          o-->DeleteRequestProto  | |
    +--------------------------------------+                                                          |                       | |
              auto | gen                                 ClientProtocol                        | 11   |                       | |
                   |                                         |                                 o--> delete()                  | |
                   |                                         |                                 |                              | |
                   v                         @ProtocolInfo(Name, Ver)                          |                              | |
    ClientNamenodeProtocol                   ClientNamenodeProtocolPB ◁ -------- ClientNamenodeProtocolServerSideTranslatorPB | |
         |                                         |                                /                          ◆              | |
         |                                         |                 +-------------/                           |              | |
         |      BlockingInterface ◁ ---------------+                 |                                         | server       | |
         |            △                                              |                                         +----------------+
         |            |                                              v                                                        |
         |            |                             BlockingService(impl) <---------------------------------------------------+
         |       BlockingStub  <----+                 ^      |
         |                          |                 |      |
         |                          | new             |      o--> getDescriptorForType()
         |                          |                 |      |
         o---> newBlockingStub() ---+                 |      |
         |                                            |      o--> getRequestPrototype()
         |                                            |      |
         o---> newReflectiveBlockingService()---------+      |
                                                             o--> getResponsePrototype()
                                                             |
                                                             |
                                                             o--> callBlockingMethod()
                                                             |        |
                                                             |        |  10
                                                             |        o--> impl.delete()
```

Delete操作从Namenode类出发经过NameNodeRpcServer启动各种服务, 最终回到NameNodeRpcServer中的delete方法.
ipc.Server: 负责网络收发 (基类)
RPC.Server: 负责PB协议维护
ProtobufRpcEngine.Server: 负责执行call
