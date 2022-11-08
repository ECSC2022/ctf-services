<?php

namespace App\Service\Analysis\Methods;

use App\Model\Analysis\AnalysisResult;
use App\Model\Analysis\EMLAnalysisResult;
use App\Model\Analysis\MailPartAnalysisResult;
use App\Model\DigitalItem;
use App\Model\User;
use App\Service\Analysis\AnalysisMethod;

class EmlAnalysisMethod extends AnalysisMethod
{
    public function __construct()
    {
        parent::__construct("eml");
    }

    public function run(?User $user, DigitalItem $item, string $data): array
    {
        $stream = fopen('php://memory', 'r+');
        if ($stream === false) {
            return [];
        }
        fwrite($stream, $data);
        rewind($stream);

        $ret = [];
        $buffer = "";
        while ($c = fgetc($stream)) {
            $num = ord($c);
            if ((32 <= $num && $num <= 127) || $c === "\n" || $c === "\r" || $c === "\t") {
                $buffer .= $c;
            } elseif ($buffer !== "") {
                $results = $this->parseStringBlob($buffer);
                $ret = array_merge($ret, $results);
                $buffer = "";
            }
        }

        return $ret;
    }

    /**
     * @param string $data
     * @return array<AnalysisResult>
     */
    private function parseStringBlob(string $data): array
    {
        $dataSplit = explode("\r\n\r\n", $data, 2);
        if (count($dataSplit) < 3) {
            return [];
        }
        list($header, $body, $additional) = $dataSplit;

        $headers = [];

        $lastHeader = null;

        $headerRows = explode("\r\n", $header);
        foreach ($headerRows as $row) {
            if (preg_match("#^\s#", $row) === 1) {
                if ($lastHeader === null) {
                    continue;
                }
                if (is_string($headers[$lastHeader])) {
                    $headers[$lastHeader] .= $row;
                } else {
                    $lastElem = array_pop($headers[$lastHeader]);
                    $lastElem .= $row;
                    $headers[$lastHeader][] = $lastElem;
                }
            }
            list($key, $value) = explode(":", $row, 1);
            $key = trim($key);
            $value = trim($value);

            if (!isset($headers[$key])) {
                $headers[$key] = $value;
            } elseif (is_array($headers[$key])) {
                $headers[$key][] = $value;
            } else {
                $headers[$key] = [$headers[$key], $value];
            }
            $lastHeader = $key;
        }

        $subject = $headers["Subject"] ?? "";
        $to = $headers["To"] ?? [];
        if (is_string($to)) {
            $to = [$to];
        }
        $from = $headers["From"] ?? "";

        $ret = [];
        $contentType = $headers["Content-Type"] ?? "";
        if (str_starts_with($contentType, "multipart/mixed")) {
            if (preg_match("#boundary=\"(\w+)\"#", $contentType, $matches) === 1) {
                $boundary = $matches[1];
                $parts = explode("$boundary\r\n", $body);
                foreach ($parts as $part) {
                    list($partHeader, $partBody) = explode("\r\n\r\n", $part, 1);
                    $partHeaders = [];
                    foreach (explode("\r\n", $partHeader) as $header) {
                        list ($key, $value) = explode(":", $header, 1);
                        $partHeaders[trim($key)] = trim($value);
                    }
                    $ret[] = new MailPartAnalysisResult($partHeaders, $partBody);
                }
            }
        }

        return [
            new EMLAnalysisResult(
                $subject,
                $body,
                $to,
                $from,
                $headers
            ),
            ...$ret
        ];
    }
}
