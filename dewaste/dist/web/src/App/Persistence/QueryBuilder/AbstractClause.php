<?php

namespace App\Persistence\QueryBuilder;

abstract class AbstractClause
{
    abstract public function _or(AbstractClause $clause): AbstractClause;
    abstract public function _and(AbstractClause $clause): AbstractClause;

    abstract public function render(): string;
}
