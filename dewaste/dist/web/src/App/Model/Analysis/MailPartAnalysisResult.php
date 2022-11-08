<?php

namespace App\Model\Analysis;

use AssertionError;

class MailPartAnalysisResult extends AnalysisResult
{
    public const TYPE = "eml-part";

    /**
     * @param array<string> $headers
     * @param string $body
     */
    public function __construct(
        private readonly array $headers,
        private readonly string $body
    ) {
        parent::__construct(self::TYPE);
    }

    public function serialize(): string
    {
        return json_encode(
            [
                "headers" => $this->headers,
                "body" => $this->body,
            ]
        ) ?: throw new AssertionError("Could not serialize mail part analysis result");
    }

    public static function deserialize(string $data): self
    {
        $json = json_decode($data);
        assert(is_array($json));
        return new self(
            $json["headers"] ?? throw new AssertionError("Could not deserialize headers field"),
            $json["body"] ?? throw new AssertionError("Could not deserialize body field"),
        );
    }

    public function renderData(): string
    {
        return "
{$this->renderHeaders()}

$this->body
";
    }

    private function renderHeaders(): string
    {
        $ret = "";
        foreach ($this->headers as $key => $value) {
            $ret .= "$key: $value\r\n";
        }
        return $ret;
    }
}
