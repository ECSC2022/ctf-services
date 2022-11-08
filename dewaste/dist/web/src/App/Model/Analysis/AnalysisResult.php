<?php

namespace App\Model\Analysis;

abstract class AnalysisResult
{
    public ?int $id = null;

    public function __construct(public string $type)
    {
    }

    abstract public function serialize(): string;

    abstract public function renderData(): string;
}
