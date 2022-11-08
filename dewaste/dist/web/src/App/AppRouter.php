<?php

namespace App;

use App\Model\Controller;
use App\Model\Route;
use ReflectionClass;

class AppRouter
{
    /** @var array<string,array<string,callable>> */
    private array $routes = [];
    /** @var null|\Closure():mixed  */
    private ?\Closure $notFoundRoute = null;

    public function __construct(private readonly string $scope = Route::DEFAULT_SCOPE)
    {
    }


    /**
     * @param string|array<string> $method
     * @param string $path
     * @param callable $func
     * @return void
     */
    public function addRoute(string|array $method, string $path, callable $func): void
    {
        if (is_array($method)) {
            foreach ($method as $m) {
                $this->addRoute($m, $path, $func);
            }
            return;
        }

        if (!isset($this->routes[$method])) {
            $this->routes[$method] = [];
        }
        $this->routes[$method][$path] = $func;
    }

    /**
     * @param \Closure():mixed $func
     */
    public function setNotFoundRoute(\Closure $func): void
    {
        $this->notFoundRoute = $func;
    }

    public function handle(string $method, string $route): mixed
    {
        $routes = $this->routes[$method] ?? [];
        foreach ($routes as $path => $func) {
            if (preg_match("#^$path$#", $route, $matches) === 1) {
                return $func($matches);
            }
        }
        if ($this->notFoundRoute === null) {
            return "Not found";
        }
        return ($this->notFoundRoute)();
    }

    public static function getCurrentPath(): string
    {
        $uri = $_SERVER["REQUEST_URI"];
        return explode("?", $uri)[0];
    }

    public function addAnnotatedController(object $controller): void
    {
        $rc = new ReflectionClass($controller);
        $controllerAttributes = $rc->getAttributes(Controller::class, \ReflectionAttribute::IS_INSTANCEOF);
        $baseUrl = "";
        if ($controllerAttributes !== []) {
            $baseUrl = $controllerAttributes[0]->newInstance()->getBaseUrl();
        }

        foreach ($rc->getMethods(\ReflectionMethod::IS_PUBLIC) as $method) {
            $routeAttributes = $method->getAttributes(Route::class, \ReflectionAttribute::IS_INSTANCEOF);
            foreach ($routeAttributes as $rroute) {
                /** @var Route $route */
                $route = $rroute->newInstance();

                if (!in_array($this->scope, $route->getScope(), true)) {
                    continue;
                }

                $this->addRoute(
                    $route->getMethods(),
                    $baseUrl . $route->getPath(),
                    fn(mixed ...$args) => $controller->{$method->getName()}(...$args)
                );
            }
        }
    }
}
