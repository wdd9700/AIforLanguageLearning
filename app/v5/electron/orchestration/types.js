/**
 * Service Orchestration Framework - Type Definitions
 * 定义服务编排、管道、服务配置等核心类型
 */
/**
 * 服务状态枚举
 */
export var ServiceStatus;
(function (ServiceStatus) {
    /** 已停止 */
    ServiceStatus["STOPPED"] = "stopped";
    /** 启动中 */
    ServiceStatus["STARTING"] = "starting";
    /** 运行中 */
    ServiceStatus["RUNNING"] = "running";
    /** 预热中 */
    ServiceStatus["WARMING"] = "warming";
    /** 错误 */
    ServiceStatus["ERROR"] = "error";
    /** 已关闭 */
    ServiceStatus["SHUTDOWN"] = "shutdown";
})(ServiceStatus || (ServiceStatus = {}));
//# sourceMappingURL=types.js.map