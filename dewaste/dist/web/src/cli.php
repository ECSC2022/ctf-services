<?php

use App\Service\Analysis\AnalysisEngine;
use App\Service\DigitalItemService;
use App\Service\FileService;
use App\Service\PhysicalItemService;
use Psr\Log\LogLevel;

if (php_sapi_name() !== 'cli') {
    die("Only call from CLI.");
}

list($container, $config) = require "common.php";

$logger = new class extends \Psr\Log\AbstractLogger {
    /**
     * @param $level
     * @param Stringable|string $message
     * @param array<string,mixed> $context
     * @return void
     */
    public function log($level, \Stringable|string $message, array $context = []): void
    {
        // skip debug logging
        if ($level === LogLevel::DEBUG) {
            return;
        }

        $contextStr = "";
        if ($context !== []) {
            $contextStr = print_r($context, true);
            $contextStr = str_replace("\n", "", $contextStr);
            $contextStr = str_replace("\t", "", $contextStr);
        }

        if (is_string($level)) {
            $level = strtoupper($level);
        } else {
            $level = "UNKNOWN";
        }

        $dt = new \DateTime();
        echo "[{$dt->format("Y-m-d H:i:s")}] $level: $message $contextStr", PHP_EOL;
    }
};

$container->get(AnalysisEngine::class)->setLogger($logger);
$container->get(DigitalItemService::class)->setLogger($logger);
$container->get(FileService::class)->setLogger($logger);

if (in_array("--process-data-item", $argv)) {
    $logger->info("Starting data processing");
    /** @var DigitalItemService $service */
    $service = $container->get(DigitalItemService::class);
    $service->analyze(100);
}
if (in_array("--cleanup-files", $argv)) {
    $logger->info("Start cleaning up files");

    $fileMaxAge = (new DateTime())->sub(new DateInterval("PT1H"));
    $logger->info("Deleting files older than " . $fileMaxAge->format("Y-m-d H:i:s"));

    /** @var FileService $fileService */
    $fileService = $container->get(FileService::class);

    $removeFromFolder = function (string $folder) use ($logger, $fileService, $fileMaxAge) {
        $num_removed = $fileService->removeFilesOlderThan($folder, $fileMaxAge);
        $logger->info("Removed $num_removed files from $folder");
    };

    // old analysis files
    $removeFromFolder($config["analysis"]["file"]["tmpfolder"]);
    // old sessions
    $removeFromFolder("/tmp");
}
if (in_array("--cleanup-database", $argv)) {
    $logger->info("Start cleaning up database");

    $maxAge = (new DateTime())->sub(new DateInterval("PT1H"));
    $logger->info("Deleting items older than " . $maxAge->format("Y-m-d H:i:s"));

    /** @var DigitalItemService $digitalItemService */
    $digitalItemService = $container->get(DigitalItemService::class);
    /** @var PhysicalItemService $physicalItemService */
    $physicalItemService = $container->get(PhysicalItemService::class);

    $num_removed = $digitalItemService->removeItemsOlderThan($maxAge);
    $logger->info("Removed $num_removed digital items");
    $num_removed = $physicalItemService->removeItemsOlderThan($maxAge);
    $logger->info("Removed $num_removed physical items");
}
