---

title: 万物互联之腾讯Shadow
date: 2018-02-06 10:01:00
tags: [ IOT ]
categories: [ Note ]

---

# Shadow学习

## 1.框架API接口

```
----------------------------------------------------------------------------------------------------------------
Sample

               on_request_handler  on_message_callback on_prop_xxx_callback  event_handler


                        register_subscribe_topics    register_config_property


                                        do_report_prop_xxx()


----------------------------------------------------------------------------------------------------------------
Shadow                                                                                                       ^
                                                                                                             |
                                  IOT_Shadow_Register_Property                                               |
                                                                                                             |
                                                                                                             |
                IOT_Shadow_Update  IOT_Shadow_Get  IOT_Shadow_Subscribe  IOT_Shadow_Yield                    |
                                                                                                             |

----------------------------------------------------------------------------------------------------------- SDK
MQTT
                                                                                                             |
                       IOT_MQTT_Publish    IOT_MQTT_Subscribe  IOT_MQTT_Yield                                |
                                                                                                             |
                               send_mqtt_packet      read_mqtt_packet                                        |
                                                                                                             v
----------------------------------------------------------------------------------------------------------------

```
<!-- more -->

## 2.静态类图

```
                                      +------------------+                                                  +-----------------+
      +------------------+            |     Request      |                   +------------------+           | SubTopicHandle  |
      | RequestParams    |            +------------------+                   |  PropertyHandler |           +-----------------+
      +------------------+            |   client_token   |                   +------------------+           |     qos         |
      |   method         |   copy     |     method       |                   |     property     |           |  topic_filter   |
      |   timeout_sec    |----------->|     timer        |                   +------------------+           |  message_data   |
      |   user_context   |            |   user_context   |                   |     callback     |           +-----------------+
      +------------------+            +------------------+                   +------------------+           | message_handler |
      | request_callback |            |    callback      |                            |                     +-----------------+
      +------------------+            +------------------+                            |                              ^
                                               |                                      |                              |
                                               |                                      |                              |
                                               |          +------------------+        |                              |
                                               |          | ShadowInnerData  |        |                              |
                                               |          +------------------+        |                              |
                                               |          |   token_num      |        |                              |
                                               |          |    version       |        |                              |
                                               +----------|  request_list    |        |                              |
                                             List         |  property_list   |--------+                              |
                                                          |  result_topic    |       List                            |
                                                          +------------------+                                       |
                                                                     ^                                               |
                                                                      \                                              |
                                                                       \            +-------------------+            |
                                                                        \           | Qcloud_IoT_Shadow |            |
                                                                         \          +-------------------+   mqtt     |
                                                                          \         |      mqtt         |◆ ----+     |
  +----------------------+           +----------------------+              -------◇ |    inner_data     |      |     |
  |  ShadowInitParams    |           |  MQTTInitParams      |                       +-------------------+      |     |
  |--------------------- |           |------------------    |                       |   event_handle    |      |     |
  |   product_id         |   copy    |   product_id         |                       +-------------------+      |     |
  |   device_name        |---------->|   device_name        |                                 ◆                |     |
  |   cert_file          |           |   cert_file          |                                 | event_hander   |     |
  |   cert_key           |           |   cert_key           |                                 |                |     |
  |   auto_connect_enable|           |   auto_connect_enable|                                 |                |     |
  +----------------------+           +----------------------|                                 |                |     |
  |   event_handle       |           |   event_handle       |                                 v                |     |
  +----------------------+           +----------------------+                        +-------------------+     |     |
           ◆                                  ◆                                      | MQTTEventHandler  |     |     |
           |                                  |   event_handle                       +-------------------+     |     |
           | event_handle                     +------------------------------------> |      context      |     |     |
           +-----------------------------------------------------------------------> +-------------------+     |     |
                                                                                     |       h_fp        |     |     |
                                                           +--------------------+    +-------------------+     |     |
                                                           | Qcloud_IoT_Client  |             ^                |     |
                                                           +--------------------+             |                |     |
                                    +--------------------◇ |  network_stack     |             |                |     |
                                    |                    ◇ |     options        |             |                |     |
                                    |                   /  | list_pub_wait_ack  |             |                |     |
                                    v                  /   | list_sub_wait_ack  |             |                |     |
                           +----------------+         /    +--------------------+             |                |     |
                           |     Network    |        /     |    event_handle    |◆ -----------+                |     |
                           +----------------+        |     |    sub_handles     |                              |     |
                           |     sockfd     |        |     +--------------------+                              |     |
          +--------------◇ |ssl_conn_params |        |              ◇       ^                                  |     |
          |                +----------------+        |              |        \                                 |     |
          |                |     connect    |        |              |         \--------------------------------+     |
          |                |      read      |        |              |                                                |
          v                |      write     |        |              +------------------------------------------------+
  +-----------------+      +----------------+        |
  |SSLConnectParams |                                |
  +-----------------+                                v
  |     host        |                     +----------------------+
  |     port        |                     | MQTTConnectParams    |
  |   cert_file     |                     +----------------------+
  |   key_file      |                     |     client_id        |
  +-----------------+                     |      conn_id         |
                                          | auto_connect_enable  |
                                          | keep_alive_interval  |
                                          +----------------------+

```

## 3.时序图
```

                            Shadow               MQTT

                                                              *******
         Aircond                                           ***       ***        Qcloud Shadow                                Door
            |                                              * host:port *               |                                      |
            |                                              ***       ***               |                                      |
    init_shadow_params                                        *******                  |                                      |
            |    |                                                                     |                                      |
            |    +------> Shadow_Construct          "$shadow/operation/result/P/D"     |                                      |
            |                     |                             (cb1)                  |                                      |
            |\                    +--------> MQTT_Construct                            |                                      |
            | \                                   |                                    |<---------+                           |
            |  \                                  |              sub                   |          |                           |
            |   \                            MQTT_Subscribe   ---------------------->  |          |                           |
            |    +------> Shadow_Get[_Sync]                                            |          |                           |
            |                     |                          pub                       |          |                           |
            |                     +--------> MQTT_Publish  ------------------------->  |          |                           |
  register_config_property                                                             |          |                           |
            |    |                                                                     |          |                           |
            |    +------> Shadow_Register_Property                                     |          |                           |
            |                                                                          |          |                           |
  register_subscribe_topics                                                            |          |                           |
            |    |                                     "P/D/control"   "P/D/xxx"       |          |        "P/D/event"        |
            |    +------> Shadow_Subscribe                 (cb2)         (cb3)         |          | pub                       |
            |                     |                              sub                   |          | <-------------------------|
            |                     +--------> send_mqtt_packet -----------------------> |          | {                         |
            |                                                                          |          |  "action": "come_home",   |
  +---> loooooop                                                                       |          |  "targetDevice": "airCon" |
  |           |                                                                        |          | }                         |
  |           +---------> Shadow_Yield                                                 |          |                           |
  |                               |                                                    |          |                           |
  |                               +--------> MQTT_Yield                                |          |                           |
  |                                              |                                     |          |                           |
  |                                              |                                     |          |                           |
  |                                        read_mqtt_packet <------------------------- |-repub <--|                           |
  |                      packet type:            |                                     |          |                           |
  |                       ---------------------------------------------                |          |                           |
  |                       |          |           |         |          |                |          |                           |
  |                       v          v           v         v          v                |          |                           |
  |                     CONNACK    PUBACK     SUBACK     PUBLISH   PINGRESP            |          |                           |
  |                         \         \          |         /          /                |          |                           |
  |                          \         v         v        v          /                 |          |                           |
  |                           -------->  handle_xxx_packet  <--------                  |          |                           |
  |                                              |                                     |          |                           |
  |                                              |                                     |          |                           |
  |             on_operation_result_handler <----+----> on_message_callback     cb3    |          |                           |
  |                        (cb1)                               (cb2)                   |          |                           |
  |                          |                                   |                     |          |                           |
  |                          |                                   |                     |          |                           |
  |                +---------+----------+                        |                     |          |                           |
  |         delta  |                    | client_token           |                     |          |                           |
  |                v                    v                        |                     |          |                           |
  |      on_prop_xxx_callback    on_request_handler              |                     |          |                           |
  |                                                              v                     |          |                           |
  |    ---------------------------------------------------------------------           |          |                           |
  |             /                                                                      |          |                           |
  |            /                                                                       |          |                           |
  |           /                                                                        |          |                           |
  | deal_with_desired                                                                  |          |                           |
  |        |                                                                           |          |                           |
  |        |                                                                           |          |                           |
  |  do_report_prop_xxx                                                                |          |                           |
  |            |                                                                       |          |                           |
  |            +--------> Shaow_Update[_Sync]                                          |          |                           |
  |                              |                            pub                      |          |                           |
  |                              +-------->  MQTT_Publish -------------------------->  |----------+                           |
  |                                                        "$shadow/operation/P/D"     |                                      |
  +----- eeeeend                                                                       |                                      |
           |  |                                                                        |                                      |
           |  +---------> Shadow_Destroy                                               |                                      |
           |                                                                           |                                      |
          END                                                                          |                                      |
```

## 4.设备影子接口

```
1. IOT_Shadow_Construct
    原型: void* IOT_Shadow_Construct(ShadowInitParams *pParams);
    功能: 构造ShadowClient
    参数:
          pParams: 连接接入与连接维持阶段所需要的参数
    返回:
          0: 失败

2. IOT_Shadow_Destroy
    原型: int IOT_Shadow_Destroy(void *handle);
    功能: 销毁ShadowClient, 关闭连接
    参数:
          handle: ShadowClient实例
    返回:
          0: 成功

3. IOT_Shadow_Get
    原型: int IOT_Shadow_Get(void *handle, OnRequestCallback callback, void *userContext, uint32_t timeout_ms);
    功能: 获取设备影子文档
    参数:
          handle     :  ShadowClient结构体
          callback   :  请求响应处理回调函数
          userContext:  用户数据, 请求响应返回时通过回调函数返回
          timeout_ms :  请求超时时间, 单位:s
    返回:
          0: 成功

4. IOT_Shadow_Update
    原型: int IOT_Shadow_Update(void *handle, char *jsonDoc, size_t sizeOfBuffer, OnRequestCallback callback, void *userContext, uint32_t timeout_ms);
    功能: 异步方式更新设备影子文档
    参数:
          handle       :  ShadowClient结构体
          jsonDoc      :  更新到云端的设备文档
          sizeOfBuffer :  文档长度
          callback     :  请求响应处理回调函数
          userContext  :  用户数据, 请求响应返回时通过回调函数返回
          timeout_ms   :  请求超时时间, 单位:ms
    返回:
          0: 成功

5. IOT_Shadow_Yield
    原型: int IOT_Shadow_Yield(void *handle, uint32_t timeout_ms);
    功能: 消息接收, 心跳包管理, 超时请求处理
    参数:
          handle     :  ShadowClient实例
          timeout_ms :  超时时间, 单位:ms
    返回:
          0: 成功

6. IOT_Shadow_Publish
    原型: int IOT_Shadow_Publish(void *handle, char *topicName, PublishParams *pParams);
    功能: 发布消息(目前阶段是MQTT消息)
    参数:
          handle    : ShadowClient实例
          topicName : 主题名
          pParams   : 发布参数
    返回:
          < 0: 失败
          >=0: 成功
    TODO:
          后续修改, 需要隐藏MQTT相关结构体

7. IOT_Shadow_Subscribe
    原型: int IOT_Shadow_Subscribe(void *handle, char *topicFilter, SubscribeParams *pParams);
    功能: 订阅消息
    参数:
          handle    :   ShadowClient实例
          topicName :   主题名
          pParams   :   订阅参数
    返回:
          < 0: 失败
          >=0: 成功
    TODO:
          后续修改, 需要隐藏MQTT相关结构体

8. IOT_Shadow_Register_Property
    原型: int IOT_Shadow_Register_Property(void *handle, DeviceProperty *pProperty, OnPropResigtCallback callback);
    功能: 注册当前设备的设备属性
    参数:
          handle    : ShadowClient实例
          pProperty : 设备属性
          callback  : 设备属性更新回调处理函数
    返回:
          0: 成功

9. IOT_Shadow_UnRegister_Property
    原型: int IOT_Shadow_UnRegister_Property(void *handle, DeviceProperty *pProperty);
    功能: 删除已经注册过的设备属性
    参数:
          handle    : ShadowClient实例
          pProperty : 设备属性
    返回:
          0: 成功

10. IOT_Shadow_JSON_ConstructReport
    原型: int IOT_Shadow_JSON_ConstructReport(void *handle, char *jsonBuffer, size_t sizeOfBuffer, uint8_t count, ...);
    功能: 在JSON文档中添加reported字段
    参数:
          handle       :  ShadowClient实例
          jsonBuffer   :  为存储JSON文档准备的字符串缓冲区
          sizeOfBuffer :  缓冲区大小
          count        :  可变参数的个数, 即需上报的设备属性的个数
    返回:
          0 : 成功

11. IOT_Shadow_JSON_ConstructReportAndDesireAllNull
    原型: int IOT_Shadow_JSON_ConstructReportAndDesireAllNull(void *handle, char *jsonBuffer, size_t sizeOfBuffer, uint8_t count, ...);
    功能: 在JSON文档中添加reported字段，同时清空desired字段
    参数:
          handle       :  ShadowClient实例
          jsonBuffer   :  为存储JSON文档准备的字符串缓冲区
          sizeOfBuffer :  缓冲区大小
          count        :  可变参数的个数, 即需上报的设备属性的个数
    返回:
          0 : 成功

12. IOT_Shadow_JSON_ConstructDesireAllNull
    原型: int IOT_Shadow_JSON_ConstructDesireAllNull(void *handle, char *jsonBuffer, size_t sizeOfBuffer);
    功能: 在JSON文档中添加 "desired": null 字段
    参数:
          handle       :  ShadowClient实例
          jsonBuffer   :  为存储JSON文档准备的字符串缓冲区
          sizeOfBuffer :  缓冲区大小
    返回:
          0 : 成功
```

## 5.Sample回调函数

```
1. on_request_handler
    原型: typedef void (*OnRequestCallback)(void *handle, Method method, RequestAck requestAck, const char *jsonDoc, void *userContext);
    功能: 每次对设备影子操作请求响应的回调函数
    参数:
          handle        :  ShadowClient实例
          method        :  文档操作方式
          requestAck    :  请求响应类型
          jsonDoc       :  云端响应返回的文档
          userContext   :  用户数据
    返回:
          0 : 成功

2. on_message_callback
    原型: typedef void (*OnMessageHandler)(void *handle, MQTTMessage *message, void *userContext);
    功能: PUBLISH消息回调处理函数
    参数:
          handle        :  ShadowClient实例
          message       :  发布或接收已订阅消息的结构体数据
          userContext   :  用户数据
    TODO:
          后续修改, 需要隐藏MQTT相关结构体

3. on_prop_xxx_callback
    原型: void (*OnPropResigtCallback)(void *handle, const char *jsonVal, uint32_t length, DeviceProperty *pProperty);
    功能: 设备属性处理回调函数
    参数:
          handle    : ShadowClient实例
          jsonVal   : 设备属性值
          length    : 设备属性值长度
          pProperty : 设备属性结构体

4. event_handler
    原型: typedef void (*MQTTEventHandleFun)(void *handle, void *context, MQTTEventMsg *msg);
    功能: MQTT相关事件回调函数
    参数:
          handle   : MQTTClient 实例
          context  : MQTTClient 上下文
          msg      : MQTT事件消息
    TODO:
          后续修改, 需要隐藏MQTT相关结构体
```

## 6.调试运行Sample
```
    1. 设置Ares的Top目录, eg: export ARES_TOP_DIR=xxx
    2.  cd $ARES_TOP_DIR; make
    3. 打开两个终端启动本地模拟的引擎脚本
        cd $ARES_TOP_DIR/doc/shadow
        console1: ./rule_engine_for_operation.sh
        console2: ./rule_engine_for_event.sh
        备注:
        rule_engine_for_operation.sh 接收topic:leiot/operation/*
        rule_engine_for_event.sh 接收topic: productID/deviceName/control

    4. 再打开两个终端启动sample程序
        cd $ARES_TOP_DIR/output/release/bin
        console3: ./aircond_shadow_sample_v2
        console4: ./door_mqtt_sample come_home aircond_sample
```
