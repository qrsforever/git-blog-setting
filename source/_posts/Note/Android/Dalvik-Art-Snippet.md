---

title: Dalvik与Art虚拟机-笔记片段
date: 2017-09-05 10:07:00
tags: [ Android, VM ]
categories: [ Note ]

---

```
                                                                                                               |
                                               Java  VM                                                        |
                                   +-----------------------------+                                             |
                                   |                             |                                             |
                                   | JNI_GetDefaultJavaVMInitArgs|                                             |
                                   | JNI_CreateJavaVM            |                                             |
                                   | JNI_GetCreatedJavaVMs       |                                             |
                                   |                             |                                             |
                                   +-----------------------------+                                             |
                                                 |                                                             |
                                                 |                                                             |
                                         dlopen  |  dlsym                                                      |
                                                 |                                                             |
                      +---------------------------------------------------------+                              |
                      |                                                         |                              |
           libdvm.so  |                                                         |   libart.so                  |
                      v                                                         v                              |
      +-----------------------------+                             +-----------------------------+              |
      |                             |                             |                             |              |
      | JNI_GetDefaultJavaVMInitArgs|                             | JNI_GetDefaultJavaVMInitArgs|              |
      | JNI_CreateJavaVM            |                             | JNI_CreateJavaVM            |              |
      | JNI_GetCreatedJavaVMs       |                             | JNI_GetCreatedJavaVMs       |              |
      |                             |                             |                             |              |
      +-----------------------------+                             +-----------------------------+              |
                 Dalvik VM                                                    Art VM                           |
---------------------------------------------------------------------------------------------------------------+
                                                                       ^
app_main.cpp                                                           |
   |                                                                   | impl: 实现无缝替换
   |                                                                   |
   +--> main()                                                    JniInvocation
   |                                     *********                     ^
   +--> AppRuntime::start()          ****         ****                 |
   |                  |              *    mJavaVM    *         +-------+            pid == 0
   |                  |              ****         ****        /                   +---------------------------------------------------+
                      v                  *********           /                    |                                                   |
                AndroidRuntime                              /                     |                                                   |
                  |                                        /                      | pid > 0                                           |
                  |                                       /                       +-------------------------------------+             |
                  |---> onStarted()                      /                        |                                     |             |
                  |                                     /                         |                         |           |             |
                  |---> onVmCreated()                  /                          |                         |           |             |
                  |                                   /                           |                         |           |             |
                  |---> start()                      /                            |                         |           v             |
                  |       |                         /                             |               |         |---> handleParentProc()  |
                  |       |                        /                              |               |         |                         |
   startReg() <---|       +---> JniInvocation.init()               Zygote.forkAndSpecialize() <---+         |                         |
                  |       |                                                                       |         |---> handleChildProc()   |
                  |       +---> startVm()                                                         |         |           ^             |
                  |       |          start the virtual machine                                    |         |           |             |
                  |       |                                                                   runOnce() <---+           |             |
                  |       +---> onVmCreated()                                                               |           +-------------+
                          |          subclass impl                                                          |
                          |                                                                                 |
                          +---> startReg()                                                              ZygoteConnection
                          |          register android functions                                            ^
                          |                                                                                |
                          |                                                                                |
                          +---> env->CallStaticVoidMethod("main")                                          |
                          |                           |                                                    |
                          |                           |                                                    |
                          .                           v                                                    |
                     Shutdown VM                  ZygoteInit                                              /|
                                                      |                                         socket   / |
                                                      |                                         --------/  |
                                                      +---> main()                             /           |
                                                      |      |                                /  zygote    |
                                                      |      |                               /             |
                                                             +---> registerZygoteSocket()----              |
                                                             |                                             |
                                                             |                                             |
                                                             +---> preload()                               |
                                                             |          load classes, resources, libs      |
                                                             |                                             |
                                                             +---> gc()                                    |
                                                             |                                             |
                                                             |                            peer.runOnce()   |
                                                             +---> runSelectLoop() ------------------------+
                                                             |
                                                             |
                                                             +---> closeServerSocket()

```
<!-- more -->

----

# What are Dalvik and ART?
Dalvik is a virtual machine designed to run applications and code written in Java. It's hard to explain this without getting very technical but suffice to say it's how apps are able to work on your Android operating system. Any application written in Java code needs a Java Virtual Machine to run. Dalvik is a mobile version of a Java Virtual Machine.

When Android released the KitKat operating system in 2013, it introduced a replacement for Dalvik called ART. ART stands for Android runtime. Two years went into developing ART and its capabilities are vastly different to Dalvik

The idea is that Android devices using ART will perform better than those using Dalvik. ART's existence and it’s improved performance is made possible by the fact that modern smartphones are significantly more advanced than the first generation of Android devices.

# What's actually different between ART and Dalvik?
## Just-in-time compilation (JIT)
Before apps can be run on Android, the code behind them must be compiled into machine code (which is basically what ART and Dalvik are there for).

Dalvik uses JIT, or just-in-time compilation. What that means is whenever you use an app; the code it needs to run is compiled, but only that piece. If you use another part of the app, more code will be compiled. The compiled code is then cached so that it can be reused while you are still running the app. Code is compiled as it is needed.

This just-in-time method means that Dalvik uses relatively little memory to perform its tasks, which was ideal for earlier Android devices that had less memory.

Memory space is less of a problem for today's devices, which is what lead to the development of ART.

## Ahead-of-time compilation (AOT)
ART collects the code into a system-dependent binary by pre-storing all of it during installation. This means it only ever has to be compiled once. Because of this, apps will run faster on Android devices using ART because there's no need for the code to be compiled each time they are required to run.

The other upside of ART is that it uses native execution, which means that it runs app machine code directly. The beneficial result of native execution is that it places less strain on the CPU than Dalvik's JIT compiling. The lower CPU usage should translate into longer battery life.

There are a couple of trade-offs for this improved performance. One is that the compiled code takes up more space in your device's memory. The second is that because the code is compiled during installation, it takes longer to install apps.


# 虚拟机启动

