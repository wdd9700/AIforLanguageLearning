"use strict";
/**
 * 用户相关数据结构
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.TOPICS = exports.ErrorCode = void 0;
var ErrorCode;
(function (ErrorCode) {
    ErrorCode["VALIDATION_ERROR"] = "VALIDATION_ERROR";
    ErrorCode["AUTHENTICATION_ERROR"] = "AUTHENTICATION_ERROR";
    ErrorCode["AUTHORIZATION_ERROR"] = "AUTHORIZATION_ERROR";
    ErrorCode["NOT_FOUND"] = "NOT_FOUND";
    ErrorCode["INTERNAL_ERROR"] = "INTERNAL_ERROR";
    ErrorCode["SERVICE_UNAVAILABLE"] = "SERVICE_UNAVAILABLE";
})(ErrorCode || (exports.ErrorCode = ErrorCode = {}));
exports.TOPICS = {
    ORCHESTRATOR: 'orchestrator',
    ASR: 'asr',
    TTS: 'tts',
    CHAT: 'chat',
    SYSTEM: 'system'
};
//# sourceMappingURL=index.js.map