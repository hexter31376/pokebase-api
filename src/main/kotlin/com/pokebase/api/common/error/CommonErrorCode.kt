package com.pokebase.api.common.error

import org.springframework.http.HttpStatus

enum class CommonErrorCode(
    override val status: HttpStatus,
    override val code: String,
    override val message: String,
): ErrorCode {
    INVALID_REQUEST(
        HttpStatus.BAD_REQUEST,
        "COMMON_001",
        "요청한 값이 올바르지 않습니다."
    ),
    RESOURCE_NOT_FOUND(
        HttpStatus.NOT_FOUND,
        "COMMON_002",
        "요청한 리소스를 찾을 수 없습니다."
    ),
    METHOD_NOT_ALLOWED(
        HttpStatus.METHOD_NOT_ALLOWED,
        "COMMON_003",
        "지원하지 않는 HTTP 메서드입니다."
    ),
    NOT_ACCEPTABLE(
        HttpStatus.NOT_ACCEPTABLE,
        "COMMON_004",
        "요청한 응답 형식을 제공할 수 없습니다."
    ),
    CONTENT_TOO_LARGE(
        HttpStatus.CONTENT_TOO_LARGE,
        "COMMON_005",
        "요청 본문의 허용 크기를 초과했습니다."
    ),
    UNSUPPORTED_MEDIA_TYPE(
        HttpStatus.UNSUPPORTED_MEDIA_TYPE,
        "COMMON_006",
        "지원하지 않는 요청 본문 형식입니다."
    ),
}
