"""
找工作小助手 - 配置文件
AI智能体配置 - 丰富版
"""

import os

# 数据库配置
DB_PATH = os.path.join(os.path.dirname(__file__), 'jobhunter.db')

# 服务器配置
HOST = '0.0.0.0'
PORT = 5000
DEBUG = True

# ==================== 面试题库配置 - 含详细答案 ====================

INTERVIEW_QUESTIONS = {
    'python': [
        {
            'question': '请介绍一下Python的GIL机制及影响',
            'answer': 'GIL（Global Interpreter Lock）是Python解释器中的全局解释器锁，它确保同一时间只有一个线程在执行Python字节码。\\n\\n影响：\\n1. 多线程无法真正并行执行CPU密集型任务\\n2. 对于IO密集型任务，多线程仍然有效（线程会在IO操作时释放GIL）\\n3. 多进程可以绕过GIL限制，实现真正的并行\\n4. 可以使用C扩展（如NumPy）在C层面释放GIL\\n\\n解决方案：\\n- CPU密集型：使用多进程（multiprocessing）\\n- IO密集型：使用多线程或异步IO（asyncio）\\n- 使用Jython或IronPython（没有GIL）'
        },
        {
            'question': 'Python中列表和元组的区别是什么',
            'answer': '1. 可变性：列表可变（mutable），元组不可变（immutable）\\n2. 语法：列表用[]，元组用()\\n3. 性能：元组比列表更快，占用内存更小\\n4. 安全性：元组作为字典的key，列表不行（因为不可哈希）\\n5. 使用场景：\\n   - 列表：需要频繁增删改的数据集合\\n   - 元组：固定数据、函数多返回值、字典key、数据保护'
        },
        {
            'question': '解释一下Python的装饰器及其使用场景',
            'answer': '装饰器是一种高阶函数，用于在不修改原函数代码的情况下，给函数添加额外功能。\\n\\n原理：利用闭包，接收一个函数作为参数，返回一个新的包装函数。\\n\\n常见使用场景：\\n1. 日志记录：记录函数调用时间和参数\\n2. 权限验证：检查用户是否有权限执行函数\\n3. 缓存：@functools.lru_cache实现结果缓存\\n4. 性能计时：测量函数执行时间\\n5. 路由注册：Flask/Django中的@app.route\\n6. 重试机制：失败自动重试\\n\\n示例：\\n@timer\\ndef my_func():\\n    pass\\n等价于：my_func = timer(my_func)'
        },
        {
            'question': '什么是Python的生成器，与迭代器有什么区别',
            'answer': '生成器（Generator）是一种特殊的迭代器，使用yield关键字定义，可以暂停和恢复执行。\\n\\n区别：\\n1. 实现方式：\\n   - 迭代器：需要实现__iter__和__next__方法\\n   - 生成器：使用yield关键字，自动实现迭代器协议\\n2. 内存效率：\\n   - 迭代器：通常需要存储所有数据\\n   - 生成器：惰性求值，一次只生成一个值，内存占用极小\\n3. 状态保存：生成器可以保存执行状态，下次从yield处继续\\n\\n使用场景：处理大数据集、无限序列、文件逐行读取等。'
        },
        {
            'question': 'Python中的*args和**kwargs的作用',
            'answer': '*args和**kwargs用于接收可变数量的参数。\\n\\n*args：\\n- 接收多余的位置参数，以元组形式存储\\n- 命名习惯叫args，可以改\\n- 示例：def func(*args) -> args = (1, 2, 3)\\n\\n**kwargs：\\n- 接收多余的关键字参数，以字典形式存储\\n- 命名习惯叫kwargs\\n- 示例：def func(**kwargs) -> kwargs = {\"a\": 1, \"b\": 2}\\n\\n拆包用法：\\n- func(*[1,2,3]) 等价于 func(1,2,3)\\n- func(**{\"a\":1}) 等价于 func(a=1)'
        },
        {
            'question': 'Python中如何实现高并发',
            'answer': 'Python实现高并发的主要方式：\\n\\n1. 多线程（threading）：\\n   - 适合IO密集型任务\\n   - 受GIL限制，不能并行执行CPU密集型任务\\n\\n2. 多进程（multiprocessing）：\\n   - 适合CPU密集型任务\\n   - 每个进程有独立的GIL，可以真正并行\\n   - 开销较大，进程间通信复杂\\n\\n3. 异步IO（asyncio）：\\n   - 单线程实现并发，使用事件循环\\n   - 适合高并发IO操作（如Web服务）\\n   - 使用async/await语法\\n\\n4. 协程（gevent/eventlet）：\\n   - 基于greenlet的轻量级线程\\n   - 自动切换，无需修改代码\\n\\n5. 线程池/进程池（concurrent.futures）：\\n   - 简化线程/进程管理\\n   - 适合批量任务处理'
        },
        {
            'question': '请解释Python的内存管理机制',
            'answer': 'Python内存管理主要包括：\\n\\n1. 引用计数：\\n   - 每个对象都有引用计数器\\n   - 计数为0时立即回收内存\\n   - 简单高效，但无法处理循环引用\\n\\n2. 垃圾回收（GC）：\\n   - 分代回收：对象分为0/1/2三代\\n   - 新对象在第0代，存活越久代数越高\\n   - 代数越高，检查频率越低（优化性能）\\n   - 使用标记-清除算法处理循环引用\\n\\n3. 内存池（pymalloc）：\\n   - 小于256字节的对象使用内存池\\n   - 减少频繁申请/释放内存的开销\\n\\n4. 大对象管理：\\n   - 直接使用C的malloc/free\\n\\n查看GC：import gc; gc.get_count() / gc.collect()'
        },
        {
            'question': 'Python中的深拷贝和浅拷贝有什么区别',
            'answer': '浅拷贝（shallow copy）：\\n- 只复制对象本身，不复制内部引用的对象\\n- 新对象和原对象共享内部引用\\n- 方法：copy.copy()、切片[:]、list()\\n- 修改嵌套对象会影响原对象\\n\\n深拷贝（deep copy）：\\n- 递归复制对象及其所有引用的对象\\n- 完全独立的新对象\\n- 方法：copy.deepcopy()\\n- 修改任何层级都不会影响原对象\\n\\n示例：\\nimport copy\\na = [[1,2], [3,4]]\\nb = copy.copy(a)  # 浅拷贝\\nc = copy.deepcopy(a)  # 深拷贝\\nb[0][0] = 999  # a也会变！\\nc[0][0] = 888  # a不变'
        },
        {
            'question': '什么是Python的上下文管理器',
            'answer': '上下文管理器（Context Manager）用于管理资源的获取和释放，确保资源正确关闭。\\n\\n实现方式：\\n1. 类实现：实现__enter__和__exit__方法\\n2. 装饰器：@contextlib.contextmanager + yield\\n\\n常见用途：\\n- 文件操作：with open(\"file\") as f:\\n- 数据库连接：自动提交/回滚\\n- 线程锁：自动获取和释放锁\\n- 临时修改环境：如临时修改系统路径\\n\\n__exit__参数：exc_type, exc_val, exc_tb\\n- 可以捕获并处理异常\\n- 返回True可抑制异常传播'
        },
        {
            'question': 'Python多线程和多进程的区别及适用场景',
            'answer': '多线程（Threading）：\\n- 共享内存空间\\n- 切换开销小\\n- 受GIL限制，不能并行执行CPU密集型任务\\n- 适合IO密集型：网络请求、文件读写、数据库操作\\n\\n多进程（Multiprocessing）：\\n- 独立内存空间（需要进程间通信）\\n- 切换开销大\\n- 不受GIL限制，可以真正并行\\n- 适合CPU密集型：计算、图像处理、数据分析\\n\\n选择建议：\\n- IO密集型且并发量不大 -> 多线程\\n- IO密集型且并发量大 -> asyncio\\n- CPU密集型 -> 多进程\\n- CPU+IO混合 -> 多进程+协程'
        }
    ],
    'java': [
        {
            'question': '请介绍一下Java的内存模型',
            'answer': 'Java内存模型（JMM）定义了多线程环境下共享变量的访问规则。\\n\\n主要区域：\\n1. 堆（Heap）：所有对象实例，线程共享\\n2. 栈（Stack）：每个线程私有，存储局部变量和方法调用\\n3. 方法区/元空间：类信息、常量、静态变量\\n4. 程序计数器：当前线程执行位置\\n5. 本地方法栈：Native方法\\n\\n关键概念：\\n- 原子性：操作不可中断\\n- 可见性：一个线程修改对另一个线程可见\\n- 有序性：禁止指令重排序\\n\\n实现机制：\\n- volatile：保证可见性和有序性\\n- synchronized：保证原子性、可见性、有序性\\n- happens-before规则'
        },
        {
            'question': 'Java中HashMap的实现原理',
            'answer': 'HashMap基于数组+链表/红黑树实现。\\n\\n核心原理：\\n1. 哈希计算：key.hashCode() ^ (hashCode >>> 16)\\n2. 定位桶：(n-1) & hash\\n3. 冲突处理：链表法（JDK8后链表长度>8转为红黑树）\\n\\n关键参数：\\n- 默认容量：16\\n- 负载因子：0.75\\n- 扩容阈值：容量 * 负载因子\\n- 树化阈值：8（链表转红黑树）\\n- 反树化阈值：6（红黑树转链表）\\n\\n扩容机制：\\n- 容量翻倍，重新哈希\\n- JDK8优化：扩容时不需要重新计算hash，只需判断高位\\n\\n线程安全：\\n- HashMap非线程安全\\n- 并发使用：ConcurrentHashMap或Collections.synchronizedMap'
        },
        {
            'question': '什么是Java的多线程，如何保证线程安全',
            'answer': 'Java多线程允许程序同时执行多个任务。\\n\\n创建线程的方式：\\n1. 继承Thread类\\n2. 实现Runnable接口\\n3. 实现Callable接口（有返回值）\\n4. 线程池（推荐）\\n\\n保证线程安全的方法：\\n1. synchronized关键字：\\n   - 同步方法、同步代码块\\n   - 可重入锁，自动释放\\n\\n2. Lock接口（ReentrantLock）：\\n   - 更灵活的锁控制\\n   - 支持公平锁、可中断、超时获取\\n\\n3. 原子类（AtomicInteger等）：\\n   - CAS操作，无锁实现\\n\\n4. 并发集合：\\n   - ConcurrentHashMap、CopyOnWriteArrayList等\\n\\n5. ThreadLocal：\\n   - 线程本地变量，每个线程独立副本'
        },
        {
            'question': '解释一下Java的反射机制及其应用',
            'answer': '反射（Reflection）是在运行时动态获取类的信息并操作对象的能力。\\n\\n核心类：\\n- Class：类的元信息\\n- Field：字段\\n- Method：方法\\n- Constructor：构造器\\n\\n常用操作：\\n- Class.forName(\"com.example.User\")\\n- clazz.getDeclaredMethods()\\n- method.setAccessible(true)\\n- method.invoke(obj, args)\\n\\n应用场景：\\n1. 框架开发：Spring的依赖注入、AOP\\n2. 序列化/反序列化：JSON转换\\n3. 动态代理：JDK动态代理\\n4. 单元测试：Mock对象\\n5. 注解处理：运行时读取注解\\n\\n缺点：性能较低，破坏封装性'
        },
        {
            'question': 'Spring Boot的核心注解有哪些',
            'answer': '核心注解：\\n\\n1. @SpringBootApplication：\\n   - 组合注解 = @Configuration + @EnableAutoConfiguration + @ComponentScan\\n\\n2. @RestController：\\n   - @Controller + @ResponseBody\\n   - 返回JSON/XML而非视图\\n\\n3. @RequestMapping / @GetMapping / @PostMapping等：\\n   - 映射HTTP请求到处理方法\\n\\n4. @Autowired / @Resource：\\n   - 自动注入依赖\\n\\n5. @Service / @Repository / @Component：\\n   - 声明Bean的角色\\n\\n6. @Value：\\n   - 注入配置属性\\n\\n7. @ConfigurationProperties：\\n   - 批量注入配置\\n\\n8. @Transactional：\\n   - 声明式事务管理'
        },
        {
            'question': 'JVM调优有哪些经验',
            'answer': 'JVM调优主要方面：\\n\\n1. 堆内存设置：\\n   - -Xms和-Xmx设为相同值，避免动态扩容\\n   - 新生代:老年代 = 1:2 或 1:3\\n\\n2. 垃圾回收器选择：\\n   - 低延迟：G1、ZGC、Shenandoah\\n   - 高吞吐：Parallel GC\\n   - 小内存：Serial GC\\n\\n3. GC日志分析：\\n   - -Xloggc:gc.log\\n   - 分析Full GC频率和耗时\\n\\n4. 内存泄漏排查：\\n   - jmap生成堆转储\\n   - MAT工具分析\\n\\n5. 线程问题：\\n   - jstack分析线程状态\\n   - 排查死锁\\n\\n6. 常用工具：\\n   - jconsole、jvisualvm、arthas'
        }
    ],
    'frontend': [
        {
            'question': '请介绍一下Vue.js的生命周期',
            'answer': 'Vue 2生命周期钩子（按执行顺序）：\\n\\n1. beforeCreate：实例初始化，数据观测和事件配置之前\\n2. created：实例创建完成，可访问数据，但DOM未生成\\n3. beforeMount：挂载开始之前，模板编译完成\\n4. mounted：挂载完成，DOM已生成，可访问el\\n5. beforeUpdate：数据更新时，DOM重新渲染之前\\n6. updated：DOM重新渲染完成\\n7. beforeDestroy：实例销毁之前，可清理资源\\n8. destroyed：实例销毁完成\\n\\nVue 3变化：\\n- beforeDestroy -> beforeUnmount\\n- destroyed -> unmounted\\n- 新增：setup()组合式API'
        },
        {
            'question': '什么是前端路由，如何实现',
            'answer': '前端路由是在不刷新页面的情况下，根据URL变化切换页面内容的技术。\\n\\n实现方式：\\n\\n1. Hash模式（location.hash）：\\n   - URL格式：/#/path\\n   - 通过hashchange事件监听\\n   - 兼容性好，不需要服务端配置\\n   - 示例：Vue Router的hash模式\\n\\n2. History模式（HTML5 History API）：\\n   - URL格式：/path（正常URL）\\n   - 使用pushState/replaceState\\n   - 需要服务端配置，刷新404问题\\n   - 示例：Vue Router的history模式\\n\\n3. Memory模式：\\n   - 不操作URL，只在内存中维护状态\\n   - 用于非浏览器环境（如移动端App）'
        },
        {
            'question': '解释一下CSS的盒模型',
            'answer': 'CSS盒模型是元素在页面中占据空间的计算方式。\\n\\n标准盒模型（content-box）：\\n- 元素总宽度 = width + padding + border + margin\\n- width只包含content\\n\\n怪异盒模型（border-box）：\\n- 元素总宽度 = width + margin\\n- width包含content + padding + border\\n- 设置：box-sizing: border-box\\n\\n组成部分（从内到外）：\\n1. Content：内容区域\\n2. Padding：内边距\\n3. Border：边框\\n4. Margin：外边距\\n\\n推荐使用border-box，更直观易算。'
        },
        {
            'question': 'JavaScript中的闭包是什么，有什么应用',
            'answer': '闭包（Closure）是函数及其引用的外部变量的组合，即使外部函数执行完毕，内部函数仍可访问外部变量。\\n\\n形成条件：\\n1. 函数嵌套\\n2. 内部函数引用外部函数的变量\\n3. 内部函数被返回或传递到外部使用\\n\\n应用场景：\\n1. 数据私有化（模拟私有变量）：\\n   function Counter() { let count = 0; return { add: () => ++count } }\\n\\n2. 函数柯里化：\\n   const add = a => b => a + b\\n\\n3. 回调函数和异步操作：\\n   保持对特定状态的引用\\n\\n4. 防抖和节流：\\n   保存定时器状态\\n\\n注意事项：\\n- 闭包会导致内存泄漏（变量无法被GC回收）\\n- 循环中使用闭包要注意let/const和var的区别'
        },
        {
            'question': '什么是响应式设计，如何实现',
            'answer': '响应式设计（Responsive Design）是让网页在不同设备和屏幕尺寸下都能良好展示的设计方法。\\n\\n实现方式：\\n\\n1. 媒体查询（Media Queries）：\\n   @media (max-width: 768px) { ... }\\n   @media (min-width: 769px) and (max-width: 1024px) { ... }\\n\\n2. 弹性布局（Flexbox）：\\n   display: flex\\n   适合一维布局（行或列）\\n\\n3. 网格布局（Grid）：\\n   display: grid\\n   适合二维布局（行和列）\\n\\n4. 相对单位：\\n   - %、vw/vh、em/rem\\n   - rem基于根字体大小，适合整体缩放\\n\\n5. 流式图片：\\n   img { max-width: 100%; height: auto; }\\n\\n6. 移动优先（Mobile First）：\\n   先写移动端样式，再用min-width扩展'
        },
        {
            'question': '前端性能优化有哪些方法',
            'answer': '前端性能优化方法：\\n\\n1. 加载优化：\\n   - 代码分割（Code Splitting）\\n   - 懒加载（Lazy Load）图片和组件\\n   - 预加载关键资源（preload/prefetch）\\n   - 使用CDN\\n   - Gzip/Brotli压缩\\n\\n2. 渲染优化：\\n   - 减少重绘（Repaint）和回流（Reflow）\\n   - 使用transform和opacity（GPU加速）\\n   - 虚拟列表（长列表优化）\\n   - 防抖和节流事件处理\\n\\n3. 资源优化：\\n   - 图片压缩、使用WebP格式\\n   - 字体优化（font-display: swap）\\n   - 移除未使用的CSS/JS（Tree Shaking）\\n\\n4. 缓存优化：\\n   - HTTP缓存策略\\n   - Service Worker离线缓存\\n\\n5. 网络优化：\\n   - HTTP/2多路复用\\n   - 减少HTTP请求数量'
        }
    ],
    'test': [
        {
            'question': '什么是单元测试、集成测试、系统测试',
            'answer': '三种测试的区别：\\n\\n1. 单元测试（Unit Testing）：\\n   - 测试最小代码单元（函数、方法）\\n   - 隔离依赖，使用Mock\\n   - 由开发人员编写\\n   - 工具：JUnit、pytest、Jest\\n   - 特点：快速、频繁、自动化\\n\\n2. 集成测试（Integration Testing）：\\n   - 测试多个模块/服务之间的交互\\n   - 验证接口和数据流\\n   - 工具：Postman、Selenium\\n   - 特点：关注模块间的协作\\n\\n3. 系统测试（System Testing）：\\n   - 测试完整的系统功能\\n   - 验证需求是否满足\\n   - 包括功能测试、性能测试、安全测试等\\n   - 特点：端到端测试，接近用户场景'
        },
        {
            'question': '如何设计测试用例',
            'answer': '测试用例设计方法：\\n\\n1. 等价类划分：\\n   - 将输入划分为有效等价类和无效等价类\\n   - 每个等价类选一个代表测试\\n\\n2. 边界值分析：\\n   - 测试边界及边界附近的值\\n   - 如：0、最大值、最小值、空值\\n\\n3. 判定表驱动：\\n   - 多条件组合时使用\\n   - 列出所有条件组合和预期结果\\n\\n4. 场景法/流程图：\\n   - 基于业务流程设计\\n   - 覆盖基本流和备选流\\n\\n5. 错误推测法：\\n   - 基于经验推测容易出错的地方\\n\\n6. 正交实验法：\\n   - 多因素多水平时减少用例数量\\n\\n用例要素：编号、标题、前置条件、测试步骤、预期结果、优先级'
        },
        {
            'question': '什么是自动化测试，有哪些工具',
            'answer': '自动化测试是使用脚本和工具自动执行测试的过程。\\n\\n优势：\\n- 提高测试效率和覆盖率\\n- 减少人为错误\\n- 支持持续集成/持续交付\\n- 可重复执行\\n\\n常用工具：\\n\\n1. UI自动化：\\n   - Selenium（Web，多语言支持）\\n   - Cypress（前端，现代框架友好）\\n   - Playwright（微软出品，多浏览器）\\n   - Appium（移动端）\\n\\n2. API自动化：\\n   - Postman + Newman\\n   - REST Assured（Java）\\n   - pytest + requests（Python）\\n\\n3. 单元测试：\\n   - JUnit/TestNG（Java）\\n   - pytest/unittest（Python）\\n   - Jest/Mocha（JavaScript）\\n\\n4. 性能测试：\\n   - JMeter、LoadRunner、Gatling'
        },
        {
            'question': '什么是缺陷的生命周期',
            'answer': '缺陷（Bug）的生命周期：\\n\\n1. 新建（New）：\\n   - 测试人员发现并提交缺陷\\n\\n2. 确认（Confirmed/Open）：\\n   - 开发/测试负责人确认是有效缺陷\\n\\n3. 分配（Assigned）：\\n   - 分配给相关开发人员修复\\n\\n4. 修复中（In Progress）：\\n   - 开发人员正在修复\\n\\n5. 已修复（Fixed/Resolved）：\\n   - 开发人员修复完成，提交测试\\n\\n6. 验证（Verified）：\\n   - 测试人员验证修复结果\\n\\n7. 关闭（Closed）：\\n   - 验证通过，关闭缺陷\\n\\n其他状态：\\n- 拒绝（Rejected）：不是缺陷或重复提交\\n- 延期（Deferred）：暂不修复\\n- 重新打开（Reopened）：验证未通过'
        },
        {
            'question': '性能测试的指标有哪些',
            'answer': '性能测试核心指标：\\n\\n1. 响应时间（Response Time）：\\n   - 从请求到收到响应的时间\\n   - 通常关注平均响应时间、P90、P99\\n\\n2. 吞吐量（Throughput）：\\n   - 单位时间处理的请求数（TPS/QPS）\\n   - TPS：每秒事务数\\n   - QPS：每秒查询数\\n\\n3. 并发用户数：\\n   - 同时在线操作的用户数\\n   - 区分并发用户和在线用户\\n\\n4. 资源利用率：\\n   - CPU使用率、内存使用率\\n   - 磁盘IO、网络带宽\\n\\n5. 错误率：\\n   - 失败请求占总请求的比例\\n\\n6. 稳定性指标：\\n   - 长时间运行的内存泄漏\\n   - 系统是否逐渐变慢'
        }
    ],
    'data': [
        {
            'question': '请解释SQL中的索引原理及优化',
            'answer': '索引原理：\\n\\n1. B+树索引（InnoDB默认）：\\n   - 非叶子节点存储键值和指针\\n   - 叶子节点存储实际数据（聚簇索引）或主键（非聚簇索引）\\n   - 叶子节点之间通过链表连接，适合范围查询\\n\\n2. 哈希索引：\\n   - 精确匹配效率高\\n   - 不支持范围查询和排序\\n\\n索引优化原则：\\n1. 最左前缀原则：联合索引按最左列开始匹配\\n2. 避免在索引列上使用函数或运算\\n3. 选择性高的列建索引（区分度>0.1）\\n4. 避免过多索引（影响写性能）\\n5. 覆盖索引：查询字段都在索引中，避免回表\\n6. 定期分析和优化表（ANALYZE TABLE）'
        },
        {
            'question': '请介绍Pandas的核心数据结构',
            'answer': 'Pandas两个核心数据结构：\\n\\n1. Series（一维）：\\n   - 类似带标签的数组\\n   - 由数据和索引组成\\n   - 创建：pd.Series([1,2,3], index=[\"a\",\"b\",\"c\"])\\n\\n2. DataFrame（二维）：\\n   - 类似电子表格或SQL表\\n   - 由多个Series组成，共享行索引\\n   - 创建：pd.DataFrame({\"A\": [1,2], \"B\": [3,4]})\\n\\n常用操作：\\n- 选择：df[\"col\"]、df.loc[]、df.iloc[]\\n- 过滤：df[df[\"A\"] > 0]\\n- 聚合：df.groupby(\"A\").sum()\\n- 合并：pd.merge()、df.concat()\\n- 透视：df.pivot_table()'
        },
        {
            'question': '什么是ETL流程',
            'answer': 'ETL（Extract-Transform-Load）是数据仓库的核心流程。\\n\\n1. Extract（抽取）：\\n   - 从各种数据源获取数据\\n   - 数据源：数据库、API、日志、文件等\\n   - 方式：全量抽取、增量抽取\\n\\n2. Transform（转换）：\\n   - 数据清洗：去重、处理缺失值、异常值\\n   - 数据转换：格式转换、单位转换\\n   - 数据加工：聚合、关联、计算衍生字段\\n   - 数据验证：规则检查、一致性校验\\n\\n3. Load（加载）：\\n   - 将处理后的数据加载到目标系统\\n   - 目标：数据仓库、数据湖、BI系统\\n   - 方式：全量加载、增量加载\\n\\n现代变体：ELT（先加载后转换，利用大数据平台算力）'
        },
        {
            'question': '请解释机器学习中的过拟合和欠拟合',
            'answer': '过拟合（Overfitting）：\\n- 模型在训练集上表现很好，但在测试集上表现差\\n- 原因：模型过于复杂，学习了噪声\\n- 表现：训练误差低，测试误差高\\n- 解决：正则化、Dropout、早停、增加数据、简化模型\\n\\n欠拟合（Underfitting）：\\n- 模型在训练集和测试集上表现都不好\\n- 原因：模型过于简单，未能捕捉数据规律\\n- 表现：训练误差和测试误差都高\\n- 解决：增加特征、使用更复杂模型、减少正则化、增加训练轮数\\n\\n判断方法：\\n- 学习曲线（Learning Curve）\\n- 交叉验证分数'
        }
    ],
    'product': [
        {
            'question': '请介绍一个你最喜欢的产品及原因',
            'answer': '回答框架（STAR法则）：\\n\\n1. 选择产品：\\n   - 选择熟悉且有深度的产品\\n   - 最好是面试公司的产品或竞品\\n\\n2. 结构化分析：\\n   - 产品定位：解决什么问题，目标用户是谁\\n   - 核心功能：最打动你的功能点\\n   - 用户体验：交互设计、视觉设计\\n   - 商业模式：如何盈利\\n   - 竞争优势：与竞品相比的优势\\n\\n3. 示例（以微信为例）：\\n   - 定位：连接一切的超级App\\n   - 核心：即时通讯 + 朋友圈 + 小程序生态\\n   - 体验：简洁的界面，低学习成本\\n   - 优势：社交关系链壁垒，小程序生态\\n\\n4. 可以提出改进建议，展示批判性思维'
        },
        {
            'question': '如何评估一个产品功能的价值',
            'answer': '功能价值评估方法：\\n\\n1. 用户价值：\\n   - 解决什么用户痛点\\n   - 影响多少用户\\n   - 用户满意度提升程度\\n\\n2. 商业价值：\\n   - 预期收入增长\\n   - 成本节约\\n   - 用户留存/活跃度提升\\n\\n3. 技术可行性：\\n   - 开发成本\\n   - 技术难度和风险\\n   - 维护成本\\n\\n4. 评估框架：\\n   - RICE模型：Reach（影响范围）× Impact（影响程度）× Confidence（信心度）/ Effort（工作量）\\n   - KANO模型：基本型、期望型、兴奋型需求\\n   - 价值/复杂度矩阵\\n\\n5. 数据验证：\\n   - A/B测试验证假设\\n   - MVP快速验证'
        },
        {
            'question': '什么是AARRR模型',
            'answer': 'AARRR是用户生命周期分析的漏斗模型，又称海盗指标。\\n\\n1. Acquisition（获取）：\\n   - 用户如何找到你\\n   - 指标：新增用户、获客成本（CAC）、渠道转化率\\n\\n2. Activation（激活）：\\n   - 用户首次体验到产品价值\\n   - 指标：注册率、首次使用完成率、激活率\\n\\n3. Retention（留存）：\\n   - 用户是否持续使用\\n   - 指标：次日留存、7日留存、30日留存\\n\\n4. Revenue（收入）：\\n   - 用户如何付费\\n   - 指标：ARPU、LTV、付费转化率\\n\\n5. Referral（推荐）：\\n   - 用户是否愿意推荐\\n   - 指标：NPS评分、病毒系数（K-factor）\\n\\n应用：识别产品瓶颈，优化转化漏斗'
        }
    ],
    'algorithm': [
        {
            'question': '请解释时间复杂度和空间复杂度',
            'answer': '时间复杂度：算法执行时间随输入规模增长的变化趋势。\\n\\n常见时间复杂度（从小到大）：\\n- O(1)：常数时间，如数组随机访问\\n- O(log n)：对数时间，如二分查找\\n- O(n)：线性时间，如遍历数组\\n- O(n log n)：线性对数，如快速排序、归并排序\\n- O(n²)：平方时间，如冒泡排序、双重循环\\n- O(2^n)：指数时间，如递归求解斐波那契\\n- O(n!)：阶乘时间，如全排列\\n\\n空间复杂度：算法执行过程中额外占用的存储空间。\\n\\n注意：\\n- 大O表示法表示上界（最坏情况）\\n- 通常关注最高阶项，忽略常数和低阶项\\n- 时间换空间 或 空间换时间的权衡'
        },
        {
            'question': '什么是动态规划，举例说明',
            'answer': '动态规划（DP）是将复杂问题分解为子问题，通过保存子问题的解来避免重复计算。\\n\\n核心思想：\\n1. 最优子结构：问题的最优解包含子问题的最优解\\n2. 重叠子问题：子问题会被重复计算\\n3. 状态转移方程：定义如何从子问题构建当前问题的解\\n\\n经典例题：\\n\\n1. 斐波那契数列：\\n   dp[i] = dp[i-1] + dp[i-2]\\n\\n2. 爬楼梯（每次1或2步）：\\n   dp[i] = dp[i-1] + dp[i-2]\\n\\n3. 0/1背包问题：\\n   dp[i][w] = max(dp[i-1][w], dp[i-1][w-weight[i]] + value[i])\\n\\n4. 最长公共子序列（LCS）\\n\\n5. 最长递增子序列（LIS）\\n\\n实现方式：\\n- 自顶向下 + 记忆化（递归）\\n- 自底向上（迭代，推荐）'
        },
        {
            'question': '常见的排序算法及复杂度',
            'answer': '常见排序算法对比：\\n\\n| 算法 | 平均时间 | 最坏时间 | 空间 | 稳定性 |\\n|------|---------|---------|------|--------|\\n| 冒泡排序 | O(n²) | O(n²) | O(1) | 稳定 |\\n| 选择排序 | O(n²) | O(n²) | O(1) | 不稳定 |\\n| 插入排序 | O(n²) | O(n²) | O(1) | 稳定 |\\n| 快速排序 | O(n log n) | O(n²) | O(log n) | 不稳定 |\\n| 归并排序 | O(n log n) | O(n log n) | O(n) | 稳定 |\\n| 堆排序 | O(n log n) | O(n log n) | O(1) | 不稳定 |\\n| 计数排序 | O(n+k) | O(n+k) | O(k) | 稳定 |\\n| 桶排序 | O(n+k) | O(n²) | O(n+k) | 稳定 |\\n\\n实际应用：\\n- 小规模数据：插入排序\\n- 通用场景：快速排序（Java的Arrays.sort）\\n- 需要稳定：归并排序（Python的Timsort）\\n- 数据范围小：计数排序'
        }
    ],
    'general': [
        {
            'question': '请做一个自我介绍',
            'answer': '自我介绍结构（1-3分钟）：\\n\\n1. 基本信息（10%）：\\n   - 姓名、学校、专业\\n   - 应聘岗位\\n\\n2. 核心经历（60%）：\\n   - 工作经历/项目经验（按时间倒序）\\n   - 使用STAR法则：情境-任务-行动-结果\\n   - 量化成果：提升了XX%，处理了XX数据量\\n\\n3. 技能匹配（20%）：\\n   - 与岗位相关的核心技能\\n   - 技术栈匹配度\\n\\n4. 结尾（10%）：\\n   - 表达对岗位的兴趣\\n   - 为什么适合这个岗位\\n\\n注意事项：\\n- 不要背诵简历，突出亮点\\n- 与岗位JD对齐\\n- 控制时间，言简意赅'
        },
        {
            'question': '你的职业规划是什么',
            'answer': '回答框架：\\n\\n1. 短期（1-2年）：\\n   - 快速融入团队，熟悉业务\\n   - 提升技术深度，成为领域专家\\n   - 示例：深入掌握XX技术栈，独立负责XX模块\\n\\n2. 中期（3-5年）：\\n   - 承担更多责任，带领小团队\\n   - 扩展技术广度，了解上下游\\n   - 示例：成为技术负责人，主导XX项目架构设计\\n\\n3. 长期（5年以上）：\\n   - 技术专家路线 或 管理路线\\n   - 根据公司发展和个人兴趣调整\\n\\n注意：\\n- 要与应聘岗位相关\\n- 体现稳定性\\n- 展示上进心但不过度野心'
        },
        {
            'question': '你的优点和缺点是什么',
            'answer': '优点（选择2-3个，与岗位相关）：\\n\\n技术岗示例：\\n- 学习能力强：快速掌握新技术，如自学XX框架并应用到项目\\n- 注重细节：代码review时发现潜在bug，编写单元测试\\n- 解决问题能力：遇到XX难题，通过XX方法解决\\n\\n缺点（选择1个，非致命且正在改进）：\\n\\n避免的缺点：\\n- 与岗位核心要求冲突的（如程序员说逻辑差）\\n- 虚假缺点（如\"工作太认真\"）\\n\\n好的示例：\\n- \"公开演讲能力有待提升，正在通过技术分享练习\"\\n- \"有时过于追求完美，正在学习权衡质量和进度\"\\n- \"对业务理解不够深入，正在主动学习业务知识\"\\n\\n关键：缺点 + 改进措施 + 已见成效'
        },
        {
            'question': '你为什么从上一家公司离职',
            'answer': '回答原则：正面、客观、不抱怨\\n\\n可以说的原因：\\n1. 职业发展：\\n   \"希望寻找更大的技术挑战和成长空间\"\\n\\n2. 技术方向：\\n   \"希望专注于XX领域，贵公司在这方面有深厚积累\"\\n\\n3. 公司变动：\\n   \"公司业务调整/搬迁，与个人规划不符\"\\n\\n4. 学习成长：\\n   \"希望接触更复杂的系统/更大的用户量\"\\n\\n绝对避免：\\n- 抱怨前公司/领导/同事\\n- 说工资低（可以委婉说\"希望薪资与能力匹配\"）\\n- 被裁员/被开除（除非客观原因）\\n- 工作太累/加班太多\\n\\n示例：\\n\"我在上家公司学到了很多，但技术栈相对固定。我希望能在贵公司接触更复杂的分布式系统，进一步提升架构设计能力。\"'
        },
        {
            'question': '你遇到过最大的挑战是什么',
            'answer': '回答框架（STAR法则）：\\n\\n1. Situation（情境）：\\n   - 项目背景、时间压力、技术难度\\n\\n2. Task（任务）：\\n   - 你的职责和目标\\n\\n3. Action（行动）：\\n   - 具体做了什么（重点）\\n   - 如何分析问题\\n   - 尝试了哪些方案\\n   - 如何协调资源\\n\\n4. Result（结果）：\\n   - 量化成果\\n   - 学到了什么\\n\\n示例：\\n\"在XX项目中，系统需要在2周内支持10倍流量增长（S）。我负责性能优化（T）。我首先通过压测定位瓶颈在数据库（A1），然后引入Redis缓存热点数据（A2），优化慢查询并添加索引（A3），最终将QPS从1000提升到15000，按时上线（R）。\"'
        },
        {
            'question': '你有什么问题想问我的',
            'answer': '必问问题（展示兴趣和思考）：\\n\\n1. 关于岗位：\\n   - \"这个岗位目前面临的最大挑战是什么？\"\\n   - \"团队的技术栈和架构是怎样的？\"\\n   - \"对这个岗位的期望是什么？\"\\n\\n2. 关于团队：\\n   - \"团队规模和组织结构如何？\"\\n   - \"团队的培养机制和晋升路径？\"\\n\\n3. 关于业务：\\n   - \"部门的核心业务和目标是什么？\"\\n   - \"未来半年的重点方向？\"\\n\\n4. 关于面试（可选）：\\n   - \"您觉得我哪些方面还需要提升？\"\\n\\n避免的问题：\\n- 薪资福利（留到HR面）\\n- 加班情况（可以委婉问工作节奏）\\n- 能在网上查到的基本信息'
        }
    ]
}

# ==================== 技能关键词库 - 丰富版 ====================

SKILL_KEYWORDS = {
    'python': ['Python', 'Django', 'Flask', 'FastAPI', 'Pandas', 'NumPy', 'Scrapy', 'Celery', 'Tornado', 'Bottle'],
    'java': ['Java', 'Spring', 'Spring Boot', 'Spring Cloud', 'MyBatis', 'Maven', 'Gradle', 'Hibernate', 'Spring Security', 'Netty'],
    'golang': ['Go', 'Gin', 'Beego', 'Echo', 'GORM', 'Go Micro', 'Buffalo'],
    'rust': ['Rust', 'Actix', 'Rocket', 'Tokio', 'Warp'],
    'frontend': ['JavaScript', 'TypeScript', 'Vue', 'React', 'Angular', 'HTML', 'CSS', 'Sass', 'Less', 'Webpack', 'Vite', 'Next.js', 'Nuxt.js'],
    'mobile': ['React Native', 'Flutter', 'iOS', 'Android', 'Swift', 'Kotlin', 'UniApp', 'WeChat Mini Program'],
    'database': ['MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Elasticsearch', 'Oracle', 'SQL Server', 'SQLite', 'ClickHouse', 'TiDB'],
    'devops': ['Docker', 'Kubernetes', 'Jenkins', 'Git', 'Linux', 'Nginx', 'AWS', 'Azure', '阿里云', 'Terraform', 'Ansible', 'Prometheus'],
    'ai': ['Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch', 'NLP', 'Computer Vision', 'Scikit-learn', 'Keras', 'OpenCV'],
    'bigdata': ['Hadoop', 'Spark', 'Flink', 'Kafka', 'Hive', 'HBase', 'Zookeeper', 'Storm', 'Druid'],
    'test': ['Selenium', 'Jest', 'JUnit', 'Postman', 'JMeter', 'Pytest', 'Cypress', 'Appium', 'TestNG'],
    'tools': ['Git', 'SVN', 'Jira', 'Confluence', 'Swagger', 'Postman', 'Fiddler', 'Charles', 'GitHub', 'GitLab'],
    'mq': ['RabbitMQ', 'Kafka', 'RocketMQ', 'ActiveMQ', 'ZeroMQ'],
    'cache': ['Redis', 'Memcached', 'Caffeine', 'Guava Cache'],
    'search': ['Elasticsearch', 'Solr', 'Lucene'],
    'security': ['OAuth', 'JWT', 'SSL', 'HTTPS', 'Firewall', 'WAF']
}

# ==================== 薪资参考数据 ====================

SALARY_DATA = {
    '后端开发': {
        '应届生': {'min': 8000, 'max': 15000, 'avg': 11000},
        '1-3年': {'min': 12000, 'max': 25000, 'avg': 18000},
        '3-5年': {'min': 20000, 'max': 40000, 'avg': 30000},
        '5-10年': {'min': 35000, 'max': 60000, 'avg': 45000},
        '10年+': {'min': 50000, 'max': 100000, 'avg': 70000}
    },
    '前端开发': {
        '应届生': {'min': 7000, 'max': 13000, 'avg': 10000},
        '1-3年': {'min': 10000, 'max': 22000, 'avg': 16000},
        '3-5年': {'min': 18000, 'max': 35000, 'avg': 26000},
        '5-10年': {'min': 30000, 'max': 50000, 'avg': 40000},
        '10年+': {'min': 45000, 'max': 80000, 'avg': 60000}
    },
    '算法工程师': {
        '应届生': {'min': 15000, 'max': 25000, 'avg': 20000},
        '1-3年': {'min': 20000, 'max': 40000, 'avg': 30000},
        '3-5年': {'min': 35000, 'max': 60000, 'avg': 45000},
        '5-10年': {'min': 50000, 'max': 100000, 'avg': 70000},
        '10年+': {'min': 80000, 'max': 150000, 'avg': 100000}
    },
    '测试工程师': {
        '应届生': {'min': 6000, 'max': 10000, 'avg': 8000},
        '1-3年': {'min': 9000, 'max': 18000, 'avg': 13000},
        '3-5年': {'min': 15000, 'max': 28000, 'avg': 22000},
        '5-10年': {'min': 25000, 'max': 45000, 'avg': 35000},
        '10年+': {'min': 40000, 'max': 70000, 'avg': 55000}
    },
    '产品经理': {
        '应届生': {'min': 8000, 'max': 15000, 'avg': 11000},
        '1-3年': {'min': 12000, 'max': 25000, 'avg': 18000},
        '3-5年': {'min': 20000, 'max': 40000, 'avg': 30000},
        '5-10年': {'min': 35000, 'max': 60000, 'avg': 45000},
        '10年+': {'min': 50000, 'max': 100000, 'avg': 70000}
    },
    '运维工程师': {
        '应届生': {'min': 7000, 'max': 12000, 'avg': 9500},
        '1-3年': {'min': 10000, 'max': 20000, 'avg': 15000},
        '3-5年': {'min': 18000, 'max': 35000, 'avg': 26000},
        '5-10年': {'min': 30000, 'max': 50000, 'avg': 40000},
        '10年+': {'min': 45000, 'max': 80000, 'avg': 60000}
    }
}

# ==================== 简历模板配置 ====================

RESUME_TEMPLATES = {
    'technical': {
        'name': '技术岗模板',
        'description': '适合开发、测试、运维等技术岗位',
        'sections': ['个人信息', '技能栈', '工作经历', '项目经验', '教育背景', '自我评价'],
        'tips': [
            '技能栈按熟练度排序',
            '项目经验使用STAR法则',
            '量化工作成果',
            '突出技术深度'
        ]
    },
    'management': {
        'name': '管理岗模板',
        'description': '适合技术管理、项目管理岗位',
        'sections': ['个人信息', '管理经验', '项目成果', '团队规模', '技术背景', '教育背景'],
        'tips': [
            '强调团队管理经验',
            '突出项目成果和业务价值',
            '展示跨部门协作能力',
            '体现技术视野'
        ]
    },
    'fresh_graduate': {
        'name': '应届生模板',
        'description': '适合应届毕业生',
        'sections': ['个人信息', '教育背景', '实习经历', '项目经验', '技能证书', '校园经历'],
        'tips': [
            '突出学习成绩和排名',
            '详细描述实习经历',
            '展示个人项目和开源贡献',
            '强调学习能力和潜力'
        ]
    },
    'senior': {
        'name': '资深专家模板',
        'description': '适合资深工程师、架构师',
        'sections': ['个人信息', '专业领域', '架构设计', '技术影响力', '项目经验', '教育背景'],
        'tips': [
            '突出架构设计经验',
            '展示技术影响力（博客、开源、演讲）',
            '强调技术选型和决策能力',
            '体现业务理解和价值创造'
        ]
    }
}

# ==================== AI智能体配置 ====================

AI_AGENT_CONFIG = {
    'name': '求职AI助手',
    'version': '2.0',
    'capabilities': [
        '简历分析',
        '简历优化',
        '岗位匹配',
        '模拟面试',
        '职业规划',
        '技能学习建议',
        '求职策略',
        '薪资评估',
        '简历模板推荐',
        '面试题库查询'
    ],
    'personality': '专业、耐心、鼓励性',
    'language': '中文'
}

# ==================== 城市薪资系数 ====================

CITY_SALARY_FACTOR = {
    '北京': 1.2,
    '上海': 1.2,
    '深圳': 1.15,
    '广州': 1.0,
    '杭州': 1.1,
    '成都': 0.85,
    '武汉': 0.8,
    '西安': 0.75,
    '南京': 0.9,
    '苏州': 0.9
}
