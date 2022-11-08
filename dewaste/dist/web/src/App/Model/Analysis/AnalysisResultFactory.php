<?php

namespace App\Model\Analysis;

class AnalysisResultFactory
{
    /** @var array<callable>  */
    public array $deserializers = [];

    public function addDeserializer(string $type, callable $method): void
    {
        $this->deserializers[$type] = $method;
    }

    public function create(string $type, string $serializedResult): AnalysisResult
    {
        $d = $this->deserializers[$type] ?? throw new \InvalidArgumentException("Unknown type: $type");
        return $d($serializedResult);
    }
}
