<?php

namespace App\UI;

use App\Service\SessionService;

class Template
{
    public function __construct(
        private string $baseDir,
        private readonly SessionService $sessionService
    ) {
        if (!str_ends_with($this->baseDir, "/")) {
            $this->baseDir .= "/";
        }
    }

    public function staticFile(string $file): string
    {
        $content = file_get_contents($this->baseDir . $file);
        if ($content === false) {
            return "File '$file' not found";
        }
        return $content;
    }

    /**
     * @param string $file
     * @param mixed ...$vars
     * @return string
     */
    public function dynamicTemplate(string $file, ...$vars): string
    {
        foreach ($vars as $_key => $_value) {
            $$_key = $_value;
        }
        $absolutePath = $this->baseDir . $file;
        if (file_exists($absolutePath)) {
            ob_start();
            include $absolutePath;
            return ob_get_clean() ?: "";
        }
        return "Template not found: $absolutePath";
    }

    public function withMainLayout(string $title, string $content): string
    {
        $user = $this->sessionService->getUser();
        return $this->dynamicTemplate("template.php", title: $title, content: $content, user: $user);
    }
}
