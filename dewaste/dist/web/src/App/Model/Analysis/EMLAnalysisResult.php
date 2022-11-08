<?php

namespace App\Model\Analysis;

use AssertionError;

class EMLAnalysisResult extends AnalysisResult
{
    public const TYPE = "eml-main";

    /**
     * @param string $subject
     * @param string $body
     * @param array<string> $recipients
     * @param string $from
     * @param array<string> $headers
     */
    public function __construct(
        private readonly string $subject,
        private readonly string $body,
        private readonly array $recipients,
        private readonly string $from,
        private readonly array $headers = [],
    ) {
        parent::__construct(self::TYPE);
    }

    public function serialize(): string
    {
        return json_encode(
            [
                "recipients" => $this->recipients,
                "headers" => $this->headers,
                "body" => $this->body,
                "subject" => $this->subject,
                "from" => $this->from,
            ]
        ) ?: throw new \AssertionError("EML Analysis object not serializable");
    }

    public static function deserialize(string $data): self
    {
        $json = json_decode($data);
        assert(is_array($json));
        return new self(
            $json["subject"] ?? throw new AssertionError("Missing subject"),
            $json["body"] ?? throw new AssertionError("Missing subject"),
            $json["recipients"] ?? throw new AssertionError("Missing subject"),
            $json["from"] ?? throw new AssertionError("Missing subject"),
            $json["headers"] ?? throw new AssertionError("Missing subject")
        );
    }

    public function renderData(): string
    {
        return "
Subject: $this->subject\r
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
