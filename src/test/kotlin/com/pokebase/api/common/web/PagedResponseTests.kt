package com.pokebase.api.common.web

import org.junit.jupiter.api.Test
import org.springframework.data.domain.Page
import org.springframework.data.domain.PageImpl
import org.springframework.data.domain.PageRequest
import tools.jackson.databind.JsonNode
import tools.jackson.databind.json.JsonMapper
import tools.jackson.module.kotlin.kotlinModule
import kotlin.test.assertEquals

class PagedResponseTests {
    private val mapper = JsonMapper.builder().addModule(kotlinModule()).build()

    @Test
    fun `serializes mapped content and page metadata in the common response`() {
        val page = PageImpl(listOf(25, 26), PageRequest.of(1, 2), 5)
            .map { "pokemon-$it" }

        val actual = mapper.readTree(mapper.writeValueAsString(CommonResponse.successPage(page)))

        val expected = mapper.readTree(
            """
            {
              "success": true,
              "data": {
                "content": ["pokemon-25", "pokemon-26"],
                "page": {"size": 2, "number": 1, "totalElements": 5, "totalPages": 3}
              },
              "error": null
            }
            """.trimIndent()
        )
        assertEquals(expected, actual)
    }

    @Test
    fun `serializes empty results with zero totals`() {
        val page = Page.empty<String>(PageRequest.of(0, 20))

        val actual = mapper.valueToTree<JsonNode>(CommonResponse.successPage(page)).path("data")

        assertEquals(mapper.readTree("[]"), actual.path("content"))
        assertEquals(20, actual.path("page").path("size").asInt())
        assertEquals(0, actual.path("page").path("number").asInt())
        assertEquals(0L, actual.path("page").path("totalElements").asLong())
        assertEquals(0, actual.path("page").path("totalPages").asInt())
    }

    @Test
    fun `out of range responses retain requested page and actual totals`() {
        val page = PageImpl(emptyList<String>(), PageRequest.of(5, 20), 25)

        val actual = mapper.valueToTree<JsonNode>(CommonResponse.successPage(page)).path("data")

        assertEquals(mapper.readTree("[]"), actual.path("content"))
        assertEquals(5, actual.path("page").path("number").asInt())
        assertEquals(25L, actual.path("page").path("totalElements").asLong())
        assertEquals(2, actual.path("page").path("totalPages").asInt())
    }
}
