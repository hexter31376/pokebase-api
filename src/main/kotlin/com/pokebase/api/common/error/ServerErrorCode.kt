package com.pokebase.api.common.error

import org.springframework.http.HttpStatus

enum class ServerErrorCode(
    override val status: HttpStatus,
    override val code: String,
    override val message: String
): ErrorCode {
    INTERNAL_SERVER_ERROR(
        HttpStatus.INTERNAL_SERVER_ERROR,
        "SERVER_001",
        "예상하지 못한 서버 에러가 발생했습니다. 개발자에게 문의해 주세요."
        ),
    SERVICE_UNAVAILABLE(
        HttpStatus.SERVICE_UNAVAILABLE,
        "SERVER_002",
        "일시적으로 서비스를 이용할 수 없습니다."
    ),
}
