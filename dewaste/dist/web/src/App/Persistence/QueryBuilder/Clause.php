<?php

namespace App\Persistence\QueryBuilder;

class Clause extends AbstractClause
{
    public function __construct(
        private string $field,
        private readonly string $operator,
        private int|float|string|Value $value
    ) {
        $this->field = strtolower($this->field);
        if (!($this->value instanceof Value)) {
            $this->value = new Value($this->value);
        }
    }

    public function _or(AbstractClause $clause): OrClause
    {
        return new OrClause($this, $clause);
    }

    public function _and(AbstractClause $clause): AndClause
    {
        return new AndClause($this, $clause);
    }

    public function render(): string
    {
        return "(\"$this->field\" $this->operator {$this->renderValue()})";
    }

    private function renderValue(): string
    {
        return (string) $this->value;
    }

    public static function equal(string $field, int|float|string $value): self
    {
        return new self($field, "=", $value);
    }

    public static function lessThan(string $field, int|float|string $value): self
    {
        return new self($field, "<", $value);
    }

    public static function greaterThan(string $field, int|float|string $value): self
    {
        return new self($field, ">", $value);
    }

    public static function lessThanOrEqual(string $field, int|float|string $value): self
    {
        return new self($field, "<=", $value);
    }

    public static function greaterThanOrEqual(string $field, int|float|string $value): self
    {
        return new self($field, ">=", $value);
    }

    public static function like(string $field, string $value): self
    {
        return new self($field, "like", $value);
    }
}
