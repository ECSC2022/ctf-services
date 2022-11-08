<?php

namespace App\Model;

#[\Attribute(\Attribute::TARGET_METHOD | \Attribute::IS_REPEATABLE)]
class Route
{
    public const DEFAULT_SCOPE = "main";

    public const GET = "GET";
    public const POST = "POST";
    public const PUT = "PUT";
    public const DELETE = "DELETE";

    /** @var string[] */
    private array $methods;
    /** @var string[] */
    private array $scopes;

    /**
     * @param string $path
     * @param string|array<string> $methods
     * @param string|array<string> $scopes
     */
    public function __construct(
        private readonly string $path,
        string|array $methods = self::GET,
        string|array $scopes = self::DEFAULT_SCOPE
    ) {
        $this->methods = is_array($methods) ? $methods : [$methods];
        $this->scopes = is_array($scopes) ? $scopes : [$scopes];
    }

    public function getPath(): string
    {
        return $this->path;
    }

    /**
     * @return string[]
     */
    public function getMethods(): array
    {
        return $this->methods;
    }

    /**
     * @return string[]
     */
    public function getScope(): array
    {
        return $this->scopes;
    }
}
