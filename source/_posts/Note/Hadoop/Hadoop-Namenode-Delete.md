---

title: Hadoop之Namenode的Delete命令代码流程
date: 2017-11-10 21:01:00
tags: [ Hadoop, Java ]
categories: [ Note ]

---

```
                     rpcServer
         NameNode ◇ -------------------------------------> NameNodeRpcServer ---------▷  NamenodeProtocols
            |                                                ◆     |                               |       +-----------------+
            |  1                                             |     |                               |       |ClientProtocol   |
            o--> initialize()                serviceRpcServer|     o---> start()                   |       |DatanodeProtocol |
            |       |                                        |     |      |                        +-----▷ |NamenodeProtocol |
            |       |                         clientRpcServer|     |      |  3                             |HAServiceProtocol|
                    o--> loadNamesystem()                    |     |      |--> clientRpcServer.start()     +-----------------+
                    |                                        |     |      |
                    o--> createRpcServer()                   |     |      |--> serverRpcServer.start()
                    |                                        |     |
                    o--> startCommonServices()               |     o---> delete()
                    |        |                               |     |
                             |  2                            |     |
                             |--> rpcServer.start()          |
                             |                               |
                                                             |
                                                             |
                                                             |
  +----------------------------------------------------------+
  |
  | ipc.Server
  |   △  |
  |   |  |----------------------------------------------------------------------------------------
  |   |  | Inner class       +---- Listener (listens on the socket, create jobs for handler threads)
  |   |  |     |             |        | ◆ 
  |   |  |     |             |        | |    readers
  |   |  |     v             |        | +------------------->  Reader()
  |   |  |                   |        |                           |
  |   |  |                   |        |                           o--> run()
  |   |  |         Selector  |        o--> run():loop             |     |    readSelector.select()
  |   |  |                   |        |     |   selector.select()       | 6
  |   |  |                   |        |     | 5                         o---> doRead() +---------------->  Connection
  |   |  |              NIO  |              o---> doAccept()                     |     |
  |   |  |                   |                      |                            o---> c.readAndProcess()
  |   |  |                   |                      |                            |            |   channelRead(ByteBuffer)
  |   |  |                   |                      o--> reader.addConnection(c)              |
  |   |  |                   |                                                                o--> processOneRpc()
  |   |  |                   |                                                                |         |
  |   |  |                   |                                                                          | 7
  |   |  |     Thread ◁ -----+---- Responder (sends responses of RPC back to clients)                   o--> processRpcRequest()
  |   |  |                   |         |                                                                            |
  |   |  |                   |         o--> run()                                                                   |
  |   |  |                   |         |                                                        Call(rpcRequest) <--o
  |   |  |                   |         |                                                              /
  |   |  |              NIO  |         o--> doRunLoop()                                              /
  |   |  |                   |         |                                                            /
  |   |  |                   |                                                                     / callQueue.put(call)
  |   |  |                   |                                                                    /
  |   |  |                   |                                                                   /
  |   |  |                   |                                                                  /
  |   |  |                   |                                                                 /
  |   |  |                   +---- Handler (handles queued calls)                             /
  |   |  |                            |                                                      /
  |   |  |                            |                                                     /
  |   |  |                            o---> run():loop                                     /
  |   |  |                                   |                                     call   /
  |   |  |                                   |                                           /
  |   |  |                                   |---> callQueue.take() --------------------/
  |   |  |                                   |
  |   |  |                                   |---> CurCall.set(call)
  |   |  |                                   | 8
  |   |  |                                   |---> call()
  |   |  |     ^                             |
  |   |  |     |                             |---> CurCall.set(null)
  |   |  |     |
  |   |  | Inner class
  |   |  |----------------------------------------------------------
  |   |  |
  |   |  o---> registerProtocolEngine()
  |   |  |
  |   |  o---> getRpcInvoker()
  |   |  |                                                                      RpcInvoker
  |   |  o---> call()         |--> responder.start()                                  △ 
  |   |  |               4    |                                                       |
  |   |  o---> start() -------+--> listener.start()                                   o---> invoke()
  |   |  |                    |                                                       |
  |   |                       |--> handler.start()                                    |
  v   |                                                                               |
 RPC.Server --------------------------------------------▷  ProtobufRpcEngine.Server   |
      |                                                         |                     |
      |                                                         |---------------------|--------------------
      o---> addProtocol()                                       | Inner class         |
        |                                                       |   |                 |
        o---> registerProtocolAndImpl()                         |   |                 |
        |                                                       |   v          ProtoBufRpcInvoker
        | 8.1                                                   |              ^      |
        o---> call()                                            |             /       |
        |      |                                         +-------------------/        o---> getProtocolImpl()
        |      |  rpcKind = RPC_PROTOCOL_BUFFER          |      |                     |
               |---> getRpcInvoker() --------------------+      |                     | 8.3
               |          |                                     |                     o---> call()
                          | 8.2                                 |   ^                        |
                          |---> call()                          |   |                        |
                                                                |   |                        |--> service.callBlockingMethod()
                                                                | Inner class                |
                                                                |-------------------------------------------


```
