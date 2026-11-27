package com.pokebase.api.common.error

import org.springframework.http.HttpStatus

interface ErrorCode {
    val status: HttpStatus
    val code: String
    val message: String
}