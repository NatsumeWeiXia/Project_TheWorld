## Project_TheWorld 环境配置

---

### 1. 本机（开发环境）

**1.1 操作系统：**Windows 11

**1.2 CPU：**32 逻辑核数

**1.3 内存：**64 GB

**1.4 Python：**3.13.1

**1.5 Java：**openjdk 17.0.16 

### 2. 服务器-1（部署环境）

**2.1 IP：**192.168.1.6

**2.2 操作系统：**Ubuntu 24.04

**2.3 用户名/密码：**

**2.4 CPU：**40 逻辑核数

**2.5 内存：**32 GB

**2.6 Python：**3.13.1

**2.7 PostgreSQL：**

​	**2.7.1 Version：**14.21

​	**2.7.2 Port：**5432

​	**2.7.3 Database for ontology：** // 用来存储元数据，包括：本体、数据属性、对象属性、能力、表映射关系

​		**2.7.3.1 name:** gensokyo

​		**2.7.3.2 Username：**akyuu

​		**2.7.3.3 Password：**akyuu

​	**2.7.4 Database for entity：** // 用来存储实体，里面的表和本体一一对应，字段也一一对应

​		**2.7.4.1 name:** memento

​		**2.7.4.2 Username：**akyuu

​		**2.7.4.3 Password：**akyuu

**2.8 Redis：**

​	**2.8.1 Version：**7.2.12

​	**2.8.2 Port：**6379

​	**2.8.3 Requirepass：**akyuu
