<?php

use App\Controllers\AppController;
use App\Controllers\FAQController;
use App\Controllers\RankingController;
use App\Controllers\RecycleController;
use App\Controllers\UserController;
use App\Model\Container;
use App\Model\Redirection;
use App\Persistence\FAQDAO;
use App\Service\DigitalItemRegistrationService;
use App\Service\DigitalItemService;
use App\Service\PhysicalItemRegistrationService;
use App\Service\PhysicalItemService;
use App\Service\RankingService;
use App\Service\SessionService;
use App\Service\UserCreationService;
use App\Service\UserLoginService;
use App\UI\Template;

list($container, $config) = require_once "common.php";

$container->set(Template::class, fn(Container $container) => new \App\UI\Template(
    __DIR__ . "/pages/",
    $container->get(SessionService::class)
));
$container->setSimple(AppController::class, Template::class);
$container->set(RecycleController::class, fn(Container $container) => new RecycleController(
    $container->get(Template::class),
    $container->get(SessionService::class),
    $container->get(UserLoginService::class),
    $container->get(UserCreationService::class),
    $container->get(PhysicalItemRegistrationService::class),
    $container->get(PhysicalItemService::class),
    $container->get(DigitalItemService::class),
    $container->get(DigitalItemRegistrationService::class),
    $config["digitalItems"]["maxFileSize"]
));
$container->setSimple(FAQController::class, Template::class, FAQDAO::class);
$container->setSimple(UserController::class, Template::class, UserLoginService::class, SessionService::class);
$container->setSimple(RankingController::class, Template::class, RankingService::class);

$router = new \App\AppRouter();
$router->addAnnotatedController($container->get(AppController::class));
$router->addAnnotatedController($container->get(RecycleController::class));
$router->addAnnotatedController($container->get(FAQController::class));
$router->addAnnotatedController($container->get(UserController::class));
$router->addAnnotatedController($container->get(RankingController::class));


try {
    $resp = $router->handle($_SERVER["REQUEST_METHOD"], \App\AppRouter::getCurrentPath());
    if (is_string($resp)) {
        echo $resp;
    }
} catch (Redirection $redirection) {
    header("Location: {$redirection->getTarget()}", response_code: 303);
    exit;
}
