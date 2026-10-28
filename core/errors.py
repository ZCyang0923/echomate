"""EchoMate 可读异常类型。"""


class EchoMateError(Exception):
    """应用级异常基类。"""


class ParserError(EchoMateError):
    """聊天记录无法解析。"""


class DuplicateImportError(EchoMateError):
    """同一人物重复导入相同文件。"""


class LLMError(EchoMateError):
    """模型调用失败。"""


class LLMConfigurationError(LLMError):
    """缺少 API Key、模型名或 SDK。"""


class LLMResponseError(LLMError):
    """模型返回内容不可用。"""


class ProfileBuildError(EchoMateError):
    """人物画像生成失败。"""


class EmbeddingError(EchoMateError):
    """Embedding 模型不可用。"""


class VectorStoreError(EchoMateError):
    """向量索引操作失败。"""


class IngestionError(EchoMateError):
    """导入流程失败。"""


class ChatError(EchoMateError):
    """聊天流程失败。"""


class MemoryError(EchoMateError):
    """记忆操作失败。"""
