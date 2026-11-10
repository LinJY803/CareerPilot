class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class LLMNotConfigured(AppError):
    def __init__(self) -> None:
        super().__init__("未配置 LLM_API_KEY，无法调用模型", 503)


class LLMError(AppError):
    def __init__(self, message: str = "模型服务暂时不可用，请稍后重试") -> None:
        super().__init__(message, 502)
