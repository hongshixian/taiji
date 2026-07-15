"""任务处理器插件层

每个任务类型实现 BaseTaskHandler 并在模块末尾调用 registry.register()。
框架通过 registry.discover() 统一加载，无需逐一感知具体类型。
"""
