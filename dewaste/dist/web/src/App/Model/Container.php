<?php

namespace App\Model;

use Psr\Container\ContainerInterface;

class Container implements ContainerInterface
{
    /** @var array<callable> $beans */
    private array $beans = [];
    /** @var array<string,object> $instances */
    private array $instances = [];

    /**
     * @template T of object
     * @param class-string<T> $class
     * @param callable(Container):T|T $func
     * @return void
     */
    public function set(string $class, mixed $func): void
    {
        if (is_callable($func)) {
            $this->beans[$class] = $func;
        } else {
            $this->instances[$class] = $func;
        }
    }

    /**
     * @param class-string $class
     * @param class-string ...$dependencies
     * @return void
     */
    public function setSimple(string $class, string ...$dependencies): void
    {
        $this->set($class, function (Container $container) use ($class, $dependencies) {
            $args = array_map(fn($x) => $container->get($x), $dependencies);
            return new $class(...$args);
        });
    }

    /**
     * @template T of object
     * @param class-string<T> $id
     * @return T
     */
    public function get(string $id): object
    {
        if (!isset($this->instances[$id])) {
            $this->instances[$id] = ($this->beans[$id] ?? throw new \RuntimeException("Cannot find $id"))($this);
        }
        return $this->instances[$id];
    }

    public function has(string $id): bool
    {
        return isset($this->instances[$id]) || isset($this->beans[$id]);
    }
}
