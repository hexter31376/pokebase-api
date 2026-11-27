package com.pokebase.api.common.web

import com.pokebase.api.common.error.CommonErrorCode
import com.pokebase.api.common.error.ServerErrorCode
import org.junit.jupiter.api.Test
import tools.jackson.databind.json.JsonMapper
import tools.jackson.module.kotlin.kotlinModule
import kotlin.test.assertEquals

class CommonResponseTests {
    private val mapper = JsonMapper.builder().addModule(kotlinModule()).build()

    @Test
    fun `success serializes a payload without an error`() {
        val response = CommonResponse.success(PokemonPayload(25, "피카츄"))

        assertJsonEquals(
            """
            {
              "success": true,
              "data": {"id": 25, "name": "피카츄"},
              "error": null
            }
            """,
            response,
        )
    }

    @Test
    fun `success without a payload serializes null data`() {
        assertJsonEquals(
            """{"success": true, "data": null, "error": null}""",
            CommonResponse.success(),
        )
    }

    @Test
    fun `success accepts an explicitly nullable payload`() {
        assertJsonEquals(
            """{"success": true, "data": null, "error": null}""",
            CommonResponse.success<PokemonPayload>(null),
        )
    }

    @Test
    fun `failure serializes the error code and field details without data`() {
        val error = ApiError.from(
            CommonErrorCode.INVALID_REQUEST,
            listOf(FieldErrorDetail("size", "1 이상 100 이하여야 합니다.")),
        )

        assertJsonEquals(
            """
            {
              "success": false,
              "data": null,
              "error": {
                "code": "COMMON_001",
                "message": "요청한 값이 올바르지 않습니다.",
                "fields": [{"field": "size", "message": "1 이상 100 이하여야 합니다."}]
              }
            }
            """,
            CommonResponse.failure(error),
        )
    }

    @Test
    fun `failure without field errors serializes an empty field list`() {
        assertJsonEquals(
            """
            {
              "success": false,
              "data": null,
              "error": {
                "code": "COMMON_002",
                "message": "요청한 리소스를 찾을 수 없습니다.",
                "fields": []
              }
            }
            """,
            CommonResponse.failure(ApiError.from(CommonErrorCode.RESOURCE_NOT_FOUND)),
        )
    }

    @Test
    fun `failure without an error preserves the current nullable error contract`() {
        assertJsonEquals(
            """{"success": false, "data": null, "error": null}""",
            CommonResponse.failure(),
        )
    }

    @Test
    fun `failure accepts server error codes through the shared factory`() {
        assertJsonEquals(
            """
            {
              "success": false,
              "data": null,
              "error": {
                "code": "SERVER_001",
                "message": "예상하지 못한 서버 에러가 발생했습니다. 개발자에게 문의해 주세요.",
                "fields": []
              }
            }
            """,
            CommonResponse.failure(ApiError.from(ServerErrorCode.INTERNAL_SERVER_ERROR)),
        )
    }

    private fun assertJsonEquals(expected: String, response: CommonResponse<*>) {
        val actual = mapper.readTree(mapper.writeValueAsString(response))
        assertEquals(mapper.readTree(expected), actual)
    }

    data class PokemonPayload(val id: Long, val name: String)
}
