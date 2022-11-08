<?php

namespace App\Persistence;

use App\Model\FAQ;
use App\Persistence\QueryBuilder\Clause;
use App\Persistence\QueryBuilder\OrClause;

class FAQDAO
{
    /** @use ParseResultsTrait<FAQ> */
    use ParseResultsTrait;

    public function __construct(private readonly PDO $db)
    {
    }

    /**
     * @param array{question:string,answer:string} $row
     * @return FAQ
     */
    private function parseRow(array $row): FAQ
    {
        return new FAQ(
            $row["question"],
            $row["answer"]
        );
    }

    /**
     * @return array<FAQ>
     */
    public function getAll(): array
    {
        $stmt = $this->db->getQueryBuilder()
            ->select("faq")
            ->query();
        return $this->parseResults($stmt);
    }

    /**
     * @param array<string> $tokens
     * @return array<FAQ>
     */
    public function searchFulltext(array $tokens): array
    {
        $clauses = [];
        foreach ($tokens as $token) {
            $clauses[] = new OrClause(
                Clause::like("question", "%$token%"),
                Clause::like("answer", "%$token%")
            );
        }

        $stmt = $this->db->getQueryBuilder()
            ->select("faq")
            ->where(...$clauses)
            ->query();
        return $this->parseResults($stmt);
    }
}
