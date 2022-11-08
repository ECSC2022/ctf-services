<?php

namespace App\Model;

#[\Attribute(\Attribute::TARGET_CLASS)]
class Controller
{
    public function __construct(private readonly string $baseUrl)
    {
    }

    public function getBaseUrl(): string
    {
        return $this->baseUrl;
    }
}
