---

title: Hadoop之FsShell的Delete命令代码流程
date: 2017-10-24 20:08:00
tags: [ Hadoop, Java ]
categories: [ Note ]

---

```
      Tool               +-----------------------------------------▷  Configured
       △                 |
       | 1               |
       o--> run()        |
       |                 |
     FsShell ------------+        Command
       |                            △
       | 0                          | 2
       o---> registerCommands()     o---> run()
       |              |             |      |
       |              |             |      |---> processOptions()
       o---> main()   |             |      |
       |              |             |      |---> processRawArguments()
                      |             |      |      |
                      |             |             |---> processArguments()
                +------------+   FsCommand        |                |
                |   Delete   |   △                                 |
                |------------|   |            expandArguments()<---|
                |    Rm    | |   |            /                    |
                |    Rmr   |-----+           /
                |    Rmdir | |              /
                |     |      |             /
                +-----|------+            /
                      |                  /
                      | 3               /
                      o---> processPath()
                      |          /
                                /
                               /
                              v      fs                                          |
                         PathData ◇ -----------------------------------------+   |
                            ◆                                                |   | 4
                            |path                                            |   o---> createFileSystem()
                            |             URI -- hdfs                        |   |                 |
                            |             ^                                  |   |                 |
                            |            /    -- local                       |   o---> get(uri)    |
                            |           /                                    |   |                 |
                            |          ◆                                     v   |                 |
                            +------> Path ---------------------------------- FileSystem            | uri = hdfs
                                      |                                          △                 |
                                      |                                          |                 |
                                      o---> getFileSystem()                      |                 | fs.initialize()
                                      |                                          |                 |
                                      |                                          |                 |
                                      |                    LocalFileSystem ------+------  DistributedFileSystem
                                                                                                  |        ◇ 
                                                                                               5  |        |
                                                                      --------- initialize() <--- o        | dfs
                                                                     /                            |        |
                    I                                               /                             |        |
     +-----▷  ClientProtocol <-------------------\             new /                              |        |
     |              |                             \               /                  delete()<--- o        |
     |              |  10                          \             /                                |        |
     |              o---> delete()                  \           /                                 |        |
     |              |                                \         /                                           |
     |                                     namenode   \       /                                            |
     |                                                 ◇     /                                             |
     |                                                DFSClient <------------------------------------------+
     |                  NameNodeProxies.createProxy()   |
     |                                       \          |
     |                                        \         o---> delete()
     |                                         \     6  |
     |                                          init<---o
     |                                                  |
     +-----------------------------------------------------------------------+
                                                                             |
                       <T>                                                   |
                   ProxyAndInfo  <------------- +                            |
                    o   |                       |                            |
                    |   |                       |                            |
                    |   o---> getProxy()        |T = ClientProtocol          |
                    |   |                       |                            |
                    |                           |                            |
                    |                           |                            |
                    |                           |     new                    |
              NameNodeProxies                   |    |------->  ClientNamenodeProtocolTranslatorPB
                    |                           |    |              ◆             |
                    |                       new |    |              |             |
                    o---> createNonHAProxy() ---+    |              |             o---> delete()
                    |            \                   |              |             |        |
                    |             \   7.2            |              |             |        |  11
                    o---> createNNProxyWithClientProtocol()         |             |        |---> rpcProxy.delete()
                    |        |                                      |
                7.1 |        |                                      | rpcProxy (is a proxy of ClientNamenodeProtocolPB)
 createProxy()  <---o        |---> RPC.setProtocolEngine()          |     |
                    |        |                    \                 |     +----------------------------------------+
                             |                     \ set            |                                              |
                             |               +----------------------|------------------------------------------+   |
                             |               |                      v                                          |   |
                             |        Conf   |    rpc.engine.ClientNamenodeProtocolPB = ProtobufRpcEngine      |   |
                             |               |                                                 |               |   |
                             |               +-------------------------------------------------+---------------+   |
                             |                                 / get                           |                   |
                             |---> RPC.getProtocolProxy()     /                                |                   |
                             |          |                    /                                 |                   |
                                        |  8                /         call          *        9 |                   |
                                        |---> getProtocolEngine()  ---------->  getProxy() <---o                   |
                                        |                                           |          |                   |
                                                                                new |          |                   |
                                                                                    |                              |
    <T>                 T =  ClientNamenodeProtocolPB                               |                              |
ProtocolProxy  <--------------------------------------------------------------------+                              | method
     |                                                                                                             |   ||
     |                   +-----> Proxy.newProxyInstance(ClientNamenodeProtocolPB) =--------------------------------+ delete
     |                   |                                      |                                                  |
     o---> getProxy()----| proxy                                |                                                  |
     |                                                          |                                                  |
     |                                                          |                       RpcInvocationHandler       |
     o---> fetchServerMethods()                                 ▽                               △                  |
     |                                -- ClientNamenodeProtocol.BlockingInterface               |                  |
     |                               /                               |                          |                  |
                                    /                                |                       Invoker               |
                   +---------------/                                 o---> delete()             |                  |
                   |                                                 |                          |  12              |
                   |                                                                            o---> invoke()<----+
                   |                                                                            |          |
   ClientNamenodeProtocol.proto:                                                                           |
   +----------------------------------------------------------------------+  constructRpcRequestHeader <---|
   |   message DeleteRequestProto {                                       |          "delete"              |
   |     required string src = 1;                                         |                                |
   |     required bool recursive = 2;                                     |                                |---> client.call()
   |   }                                                                  |                                |        |
   |                                                                      |                                         |
   |   message DeleteResponseProto {                                      |                                         |
   |       required bool result = 1;                                      |                                         |
   |   }                                                                  |    connections                          |
   |                                                                      |         -----◇  Client <----------------+
   |   service ClientNamenodeProtocol {                                   |        /           |
   |       rpc delete(DeleteRequestProto) returns(DeleteResponseProto);   |       /            |  13
   |   }                                                                  |      /             o---> call()
   |                                                                      |     /              |      |
   +----------------------------------------------------------------------+    /               |      |
                                                                              /                |      |--> createCall():call
                                                                             /                        |
                                                                            /      getConnection()<---|
                                            Thread                         /        |                 |--> conn.sendRpcRequest()
                                              △                           /         |                 |
                                              |                          /          |---> new conn    |--> call.getRpcResponse()
                                calls         |                         /           |
            Call <--------------------◇  Connection <-------------------            |---> conn.addCall()
             |                                |                                     |
             |                                |                                     |---> conn.setupIOstreams()
             o---> setRpcResponse()           o---> addCall()
             |                                |
             |           sendRpcRequest() <---o
             |                                |
             o---> getRpcResponse()           o---> setupIOstreams()
             |                                |        |
             |                                |        |---> writeConnectionHeader()
                                              | socket |
                                              |        |---> writeConnectionContext()
                                              |        |
                                              |        |---> start()
                                              |                /
                                              |               /
                                              o---> run() <---
                                              |      |
                                                     |
                                                     |---> waitForWork()
                                                     |
                                                     |---> receiveRpcResponse()
                                                                  |
                                                                  |---> call.setRpcResponse()
                                                                  |
```

实质: Java动态代理 + ProtocolBuffer
