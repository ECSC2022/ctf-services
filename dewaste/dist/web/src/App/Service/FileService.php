<?php

namespace App\Service;

use DateTimeInterface;
use Psr\Log\LoggerAwareTrait;

class FileService
{
    use LoggerAwareTrait;

    public function removeFilesOlderThan(string $directory, DateTimeInterface $timeLimit): int
    {
        $directoryIterator = new \RecursiveDirectoryIterator($directory);
        $iterator = new \RecursiveIteratorIterator($directoryIterator);

        $num_removed = 0;
        /** @var \SplFileInfo $file */
        foreach ($iterator as $file) {
            if (in_array($file->getFilename(), [".", ".."])) {
                continue;
            }

            $filename = $file->getPathname();
            $this->logger?->debug("Looking at: $filename");
            $time = new \DateTime();
            $aTimestamp = $file->getATime();
            if ($aTimestamp === false) {
                $this->logger?->info("Cannot determine last access time. Skipping...");
                continue;
            }
            $time->setTimestamp($aTimestamp);

            $this->logger?->debug("Access Time: " . $time->format("Y-m-d H:i:s"));

            if ($time < $timeLimit) {
                if (!@unlink($filename)) {
                    $this->logger?->warning("Could not remove file: $filename");
                } else {
                    $num_removed++;
                }
            }
        }

        return $num_removed;
    }
}
