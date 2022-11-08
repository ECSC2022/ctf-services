<?php

function isPostRequest(): bool
{
    return $_SERVER["REQUEST_METHOD"] === "POST";
}

function parsePostString(string $name, ?string $default = ""): ?string
{
    return isset($_POST[$name]) && is_string($_POST[$name]) ? $_POST[$name] : $default;
}

function parseGetString(string $name, ?string $default = ""): ?string
{
    return isset($_GET[$name]) && is_string($_GET[$name]) ? $_GET[$name] : $default;
}

function parsePostInt(string $name, ?int $default = 0): ?int
{
    return isset($_POST[$name]) && is_numeric($_POST[$name]) ? (int)$_POST[$name] : $default;
}

function parsePostFloat(string $name, ?float $default = 0): ?float
{
    return isset($_POST[$name]) && is_numeric($_POST[$name]) ? (float)$_POST[$name] : $default;
}

function errorBox(bool|string $msg, bool $stripTags = true): string
{
    $msg = is_bool($msg) ? "" : $msg;
    if ($stripTags) {
        $msg = htmlspecialchars($msg);
    }
    return "<p class='alert alert-danger'>$msg</p>";
}
