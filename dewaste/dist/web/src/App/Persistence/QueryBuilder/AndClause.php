<?php

namespace App\Persistence\QueryBuilder;

class AndClause extends AbstractClause
{
    /** @var AbstractClause[]  */
    private array $clauses;

    public function __construct(AbstractClause ...$clauses)
    {
        $this->clauses = $clauses;
    }

    public function _or(AbstractClause $clause): AbstractClause
    {
        return new OrClause($this, $clause);
    }

    public function _and(AbstractClause $clause): AbstractClause
    {
        $this->clauses[] = $clause;
        return $this;
    }

    public function render(): string
    {
        return "(" . implode(" AND ", array_map(fn($x) => $x->render(), $this->clauses)) . ")";
    }
}
