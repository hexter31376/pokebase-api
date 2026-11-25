package com.pokebase.api

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class PokebaseApiApplication

fun main(args: Array<String>) {
    runApplication<PokebaseApiApplication>(*args)
}
