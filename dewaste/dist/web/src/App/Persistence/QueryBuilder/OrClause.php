<?php

namespace App\Persistence\QueryBuilder;

class OrClause extends AbstractClause
{
    /** @var AbstractClause[] $clauses */
    private array $clauses;

    public function __construct(AbstractClause ...$clauses)
    {
        $this->clauses = $clauses;
    }


    public function _or(AbstractClause $clause): OrClause
    {
        $this->clauses[] = $clause;
        return $this;
    }

    public function _and(AbstractClause $clause): AndClause
    {
        return new AndClause($this, $clause);
    }

    public function render(): string
    {
        return "(" . implode(" OR ", array_map(fn($x) => $x->render(), $this->clauses)) . ")";
    }
}
