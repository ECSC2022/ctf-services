<?php

namespace App\Persistence;

use App\Model\Analysis\AnalysisResult;
use App\Model\Analysis\AnalysisResultFactory;
use App\Persistence\QueryBuilder\Clause;
use AssertionError;

class AnalysisResultDAO
{
    /** @use ParseResultsTrait<AnalysisResult> */
    use ParseResultsTrait;

    public function __construct(
        private readonly PDO $db,
        private readonly AnalysisResultFactory $analysisResultFactory
    ) {
    }

    public function insert(int $itemId, AnalysisResult $result): void
    {
        $stmt = $this->db->prepare(<<<SQL
INSERT INTO analysis_result
("digitalitemid", "type", "result")
VALUES
(?,?,?)
SQL
        );
        $serialized = $result->serialize();
        $stmt->execute([$itemId, $result->type, base64_encode($serialized)]);
        $result->id = (int) $this->db->lastInsertId();
    }

    /**
     * @param int $itemId
     * @return array<AnalysisResult>
     */
    public function getByItemId(int $itemId): array
    {
        $stmt = $this->db->getQueryBuilder()
            ->select("analysis_result")
            ->where(Clause::equal("digitalitemid", $itemId))
            ->query();
        return $this->parseResults($stmt);
    }

    /**
     * @param array{id:int,type:string,result:resource} $row
     * @return AnalysisResult
     */
    protected function parseRow(array $row): AnalysisResult
    {
        $resultContent = fgets($row["result"]);
        $result = $this->analysisResultFactory->create(
            $row["type"],
            base64_decode($resultContent ?: "", true) ?:
                throw new AssertionError("Could not decode result from the database")
        );
        $result->id = $row["id"];
        return $result;
    }
}
