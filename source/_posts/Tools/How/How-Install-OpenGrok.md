---

title: 如何使用Opengrok
date: 2017-09-13 11:05:32
tags: [ How ]
categories: [ Tools ]

---

# 环境配置

**1. 下载Opengrok和Tomcat**

<!-- more -->

>  
建立软链接
lidong@node0:/$ ls -l /opt/ | egrep "tomcat|opengrok"
lrwxrwxrwx 1 lidong   lidong         36 Sep 13 09:57 opengrok -> /data/opt/opengrok/opengrok-1.1-rc11
lrwxrwxrwx 1 lidong   lidong         37 Sep 13 09:57 tomcat -> /data/opt/tomcat/apache-tomcat-8.5.14
lidong@node0:/$ 

**2. 配置环境变量**

>  
export TOMCAT\_VERSION=8.5.14
export TOMCAT\_HOME=/data/opt/tomcat/apache-tomcat-${TOMCAT\_VERSION}
export CATALINA\_HOME=$TOMCAT\_HOME
export PATH=$TOMCAT\_HOME/bin:$PATH

<br/>

>  
export OPENGROK\_TOMCAT\_BASE=/opt/tomcat
export OPENGROK\_VERSION=1.1-rc11
export OPENGROK\_HOME=/data/opt/opengrok/opengrok-${OPENGROK\_VERSION}
export OPENGROK\_INSTANCE\_BASE=$OPENGROK\_HOME
export PATH=$OPENGROK\_HOME/bin:$PATH


# 工程配置

**1. 建工程目录**

> 
\# 创建总工程目录
cd /project/opengrok/
\#例如创建三个工程avro, hadoop, hbase
mkdir avro hadoop hbase
\# 分别创建各个工程的etc(工程私有配置),src(工程源码子目录)
mkdir avro/etc avro/src
mkdir hadoop/etc hadoop/src
mkdir hbase/etc hbase/src


**2. 设置每个项目的配置文件**

cat avro/etc/opengrok.conf 
>  
OPENGROK\_VERBOSE=yes
OPENGROK\_PROGRESS=yes
OPENGROK\_WEBAPP\_CFGADDR=localhost:9743
OPENGROK\_WEBAPP\_CONTEXT=avro
IGNORE\_PATTERNS="-i f:.\* -i d:target -i d:test"

<br\>
cat hadoop/etc/opengrok.conf 
>   
OPENGROK\_VERBOSE=yes
OPENGROK\_PROGRESS=yes
OPENGROK\_WEBAPP\_CFGADDR=localhost:9741
OPENGROK\_WEBAPP\_CONTEXT=hadoop
IGNORE\_PATTERNS="-i f:.\* -i d:target -i d:test"

<br\>
cat hbase/etc/opengrok.conf 
>  
OPENGROK\_VERBOSE=yes
OPENGROK\_PROGRESS=yes
OPENGROK\_WEBAPP\_CFGADDR=localhost:9742
OPENGROK\_WEBAPP\_CONTEXT=hbase
IGNORE\_PATTERNS="-i f:.\* -i d:target -i d:test"


**3. 创建每个项目源码目录软链接**
```  
# tree avro/src/
avro/src/
`-- avro -> /data/opt/avro/avro-src-1.8.2/
```

<br\>
```  
# tree hadoop/src/
hadoop/src/
|-- hadoop-common-project -> /data/opt/hadoop/hadoop-2.7.3-src/hadoop-common-project
|-- hadoop-hdfs-project -> /data/opt/hadoop/hadoop-2.7.3-src/hadoop-hdfs-project/
`-- hadoop-yarn-project -> /data/opt/hadoop/hadoop-2.7.3-src/hadoop-yarn-project/
```

<br\>
```  
# tree hbase/src/
hbase/src/
`-- hbase -> /data/opt/hbase/hbase-1.2.6-src
```

# 建立或更新

**1. opengrok.sh脚本**
将opengrok.sh 加入到PATH环境变量中,或者拷贝到/usr/bin
cat /usr/bin/opengrok.sh

```
#!/bin/bash

opengrok_pro_dir=`pwd`
opengrok_bin_dir=`which OpenGrok`
opengrok_bin_dir=`dirname $opengrok_bin_dir`
opengrok_top_dir=`dirname $opengrok_bin_dir`

echo "Info: opengrok_pro_dir: $opengrok_pro_dir"
echo "Info: opengrok_bin_dir: $opengrok_bin_dir"
echo "Info: opengrok_top_dir: $opengrok_top_dir"

if [[ x$opengrok_bin_dir == x ]]
then
    echo -e "\n Error: Not set path to opengrok/bin!\n"
    exit 1
fi

if [[ x$TOMCAT_HOME == x ]]
then
    echo -e "\n Error: Not set env TOMCAT_HOME!\n"
    exit 1
fi

for pro in ${@}
do
    pro_dir=$opengrok_pro_dir/$pro 
    if [ -d $pro_dir ]
    then
        if [ ! -f $pro_dir/etc/opengrok.conf ]
        then
            echo -e "\n Error: $pro_dir/etc/opengrok.conf file Not found!\n"
            continue
        fi
        $TOMCAT_HOME/bin/shutdown.sh
        sleep 3
        webapp_addr=`cat $pro_dir/etc/opengrok.conf | grep OPENGROK_WEBAPP_CFGADD | cut -d= -f2`
        if [[ x$webapp_addr == x ]]
        then
            webapp_addr=localhost:2424
        fi
        port=`echo $webapp_addr | cut -d\: -f2`
        echo -e "\n####check port($port):\n"
        netstat -anp | grep $port
        rm -rf $pro_dir/log/
        rm -rf $pro_dir/etc/configuration.xml
        if [ ! -d $pro_dir/data ]
        then
            mkdir -p $pro_dir/data 
        fi
        if [ ! -d $pro_dir/log ]
        then
            mkdir -p $pro_dir/log
        fi
        cp $opengrok_top_dir/lib/source.war ${pro_dir}.war
        unzip ${pro_dir}.war WEB-INF/web.xml
        sed -i -e 's:/var/opengrok/etc/configuration.xml:'"$pro_dir/etc/configuration.xml"':g' "WEB-INF/web.xml"    
        sed -i -e 's/localhost:2424/'"$webapp_addr"'/g' "WEB-INF/web.xml"
        zip ${pro_dir}.war -u WEB-INF/web.xml
        rm -rf WEB-INF
        rm -rf $TOMCAT_HOME/${pro_dir}*
        $TOMCAT_HOME/bin/startup.sh
        echo "Info: Wait 5s for tomcat startup"
        sleep 5
        mv ${pro_dir}.war $TOMCAT_HOME/webapps/
        OPENGROK_INSTANCE_BASE=$pro_dir OPENGROK_CONFIGURATION=$pro_dir/etc/opengrok.conf OpenGrok index 
    else
        echo "\n Error: $pro_dir directory Not found!\n"
    fi
done

```

**2. 执行脚本**

进入工程总目录
>  cd /projects/opengrok

多个
>  opengrok.sh avro hadoop hbase

单个
> opengrok.sh avro

**3. 编写index.html**
cat /opt/tomcat/webapps/source/index.html
```
<html>
    <title>Mermaid Opengrok</title>
    <style> 
        body{
            width: 50%;
            margin:0 auto;
            text-align:center
        }
    </style>

    <body>
        <h1 align="center">Opengrok</h1>
        <h2 align="left">Data Mining</h2>
        <ul>
            <li align="left"><a name="hadoop_link" href="../hadoop">Hadoop </a></li>
            <li align="left"><a name="hbase_link" href="../hbase">Hbase </a></li>
            <li align="left"><a name="avro_link" href="../avro">Avro </a></li>
        </ul>
    </body>
</html>
```

**4. 浏览器访问**
>  http://localhost:8080/source

![Opengrok-首页](http://ovhyz7ak1.bkt.clouddn.com/17-9-13/50598917.jpg)
<br/>
---------------------------------------------------------------------
<br/>
![Opengrok-Hadoop](http://ovhyz7ak1.bkt.clouddn.com/17-9-13/63523799.jpg)
