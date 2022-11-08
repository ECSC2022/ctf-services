<?php

namespace App\Model\Analysis;

class FileAnalysisResult extends AnalysisResult
{
    public const TYPE = "file";

    public function __construct(private readonly string $output)
    {
        parent::__construct(self::TYPE);
    }

    public function serialize(): string
    {
        return $this->output;
    }

    public function renderData(): string
    {
        return $this->output;
    }

    public static function deserialize(string $data): self
    {
        return new self($data);
    }
}
