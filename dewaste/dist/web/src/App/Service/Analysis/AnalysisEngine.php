<?php

namespace App\Service\Analysis;

use App\Model\Analysis\AnalysisResult;
use App\Model\DigitalItem;
use App\Model\User;
use Exception;
use Psr\Log\LoggerAwareTrait;

class AnalysisEngine
{
    use LoggerAwareTrait;

    /** @var array<AnalysisMethod> */
    private array $methods = [];

    public function addMethod(AnalysisMethod $method): void
    {
        $this->methods[] = $method;
    }

    /**
     * @param User|null $user
     * @param DigitalItem $item
     * @param string $data
     * @return array<AnalysisResult>
     */
    public function analyze(?User $user, DigitalItem $item, string $data): array
    {
        $results = [];
        foreach ($this->methods as $method) {
            $this->logger?->info("Running method: $method->name for item $item->id");
            try {
                $methodResults = $method->run($user, $item, $data);
                $results = array_merge($results, $methodResults);
            } catch (Exception $e) {
                $this->logger?->warning("Method $method->name failed", ["exception" => $e]);
                // ignore
            }
        }
        return $results;
    }
}
