<?php

namespace App\Model\Analysis;

class IniAnalysisResult extends AnalysisResult
{
    public const TYPE = "ini";

    /**
     * @param array<array<string,string>|string> $data
     */
    public function __construct(private readonly array $data)
    {
        parent::__construct(self::TYPE);
    }

    public function serialize(): string
    {
        return json_encode($this->data) ?:
            throw new \AssertionError("INI result object object not serializable");
    }

    public function renderData(): string
    {
        $ret = "";
        foreach ($this->data as $section => $elems) {
            if (is_array($elems)) {
                $ret .= "[$section]\n";
                foreach ($elems as $key => $value) {
                    $ret .= "$key = $value\n";
                }
            } else {
                $ret .= "$section = $elems\n";
            }
        }
        return $ret;
    }

    public static function deserialize(string $serialized): self
    {
        $data = json_decode($serialized, true);
        assert(is_array($data));
        return new self($data);
    }
}
