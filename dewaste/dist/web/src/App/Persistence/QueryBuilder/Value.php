<?php

namespace App\Persistence\QueryBuilder;

class Value
{
    public function __construct(private readonly int|float|string $value)
    {
    }

    public function __toString(): string
    {
        if (is_string($this->value)) {
            $enclosing = (new AlnumGenerator())->generate();
            return "\$$enclosing\$" . $this->value . "\$$enclosing\$";
        } elseif (is_int($this->value) || is_float($this->value)) {
            return "$this->value";
        }
        throw new \AssertionError("Not a valid value type: " . get_debug_type($this->value));
    }
}
