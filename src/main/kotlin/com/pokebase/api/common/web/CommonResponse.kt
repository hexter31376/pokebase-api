package com.pokebase.api.common.web

import com.pokebase.api.common.error.ErrorCode
import org.springframework.data.domain.Page
import org.springframework.data.web.PagedModel

@ConsistentCopyVisibility
data class CommonResponse<T> private constructor (
    val success: Boolean,
    val data: T?,
    val error: ApiError?
) {
    companion object {
        fun <T> success(data: T?): CommonResponse<T> = CommonResponse(true, data, null)
        fun <T : Any> successPage(page: Page<T>): CommonResponse<PagedModel<T>> =
            success(PagedModel(page))
        fun success(): CommonResponse<Unit> = CommonResponse(true, null, null)
        fun failure(error: ApiError? = null): CommonResponse<Unit> = CommonResponse(false, null, error)
    }
}

data class ApiError(
    val code: String,
    val message: String,
    val fields: List<FieldErrorDetail> = emptyList(),
) {
    companion object {
        fun from(code: ErrorCode, fields: List<FieldErrorDetail> = emptyList()): ApiError =
            ApiError(code.code, code.message, fields)
    }
}

data class FieldErrorDetail(val field: String, val message: String)
