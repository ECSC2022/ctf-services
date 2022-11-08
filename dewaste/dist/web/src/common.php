<?php

use App\Model\Analysis\AnalysisResultFactory;
use App\Model\Analysis\EMLAnalysisResult;
use App\Model\Analysis\FileAnalysisResult;
use App\Model\Analysis\IniAnalysisResult;
use App\Model\Analysis\MailPartAnalysisResult;
use App\Model\Container;
use App\Persistence\AnalysisResultDAO;
use App\Persistence\DigitalItemDAO;
use App\Persistence\FAQDAO;
use App\Persistence\PDO;
use App\Persistence\PhysicalItemDAO;
use App\Persistence\StatsDAO;
use App\Persistence\UserDAO;
use App\Service\Analysis\AnalysisEngine;
use App\Service\Analysis\Methods\IniAnalysisMethod;
use App\Service\DigitalItemService;
use App\Service\FileService;
use App\Service\PasswordCheckingService;
use App\Service\PhysicalItemRegistrationService;
use App\Service\PhysicalItemService;
use App\Service\SessionService;
use App\Service\UserCreationService;
use App\Service\UserLoginService;

require_once "vendor/autoload.php";
require "utils.php";
mt_srand(microtime(true));

$config = require __DIR__ . "/config.php";

$container = new Container();

$analysisResultFactory = new AnalysisResultFactory();
$analysisResultFactory->addDeserializer(IniAnalysisResult::TYPE, [IniAnalysisResult::class, "deserialize"]);
$analysisResultFactory->addDeserializer(EMLAnalysisResult::TYPE, [EMLAnalysisResult::class, "deserialize"]);
$analysisResultFactory->addDeserializer(
    MailPartAnalysisResult::TYPE,
    [MailPartAnalysisResult::class, "deserialize"]
);
$analysisResultFactory->addDeserializer(FileAnalysisResult::TYPE, [FileAnalysisResult::class, "deserialize"]);
$container->set(AnalysisResultFactory::class, fn() => $analysisResultFactory);

$analysisEngine = new AnalysisEngine();
$analysisEngine->addMethod(new IniAnalysisMethod());
$analysisEngine->addMethod(new \App\Service\Analysis\Methods\EmlAnalysisMethod());
$analysisEngine->addMethod(new \App\Service\Analysis\Methods\FileAnalysisMethod(
    $config["analysis"]["file"]["tmpfolder"]
));
$container->set(AnalysisEngine::class, fn() => $analysisEngine);


$dbManager = new \App\Persistence\DatabaseManager(
    $config["db"]["host"],
    $config["db"]["user"],
    $config["db"]["password"],
    $config["db"]["name"]
);
$container->set(PDO::class, fn() => $dbManager->getNewConnection());

$registerDAO = fn(string $className) => $container->setSimple($className, PDO::class);
$registerDAO(UserDAO::class);
$registerDAO(FAQDAO::class);
$registerDAO(PhysicalItemDAO::class);
$registerDAO(DigitalItemDAO::class);
$container->setSimple(AnalysisResultDAO::class, PDO::class, AnalysisResultFactory::class);
$registerDAO(StatsDAO::class);

$container->setSimple(SessionService::class);
$container->setSimple(PasswordCheckingService::class);
$container->setSimple(UserLoginService::class, UserDAO::class, SessionService::class);
$container->setSimple(
    UserCreationService::class,
    UserDAO::class,
    PasswordCheckingService::class,
    SessionService::class
);
$container->setSimple(PhysicalItemRegistrationService::class, PhysicalItemDAO::class);
$container->setSimple(PhysicalItemService::class, PhysicalItemDAO::class);
$container->setSimple(
    DigitalItemService::class,
    DigitalItemDAO::class,
    AnalysisEngine::class,
    AnalysisResultDAO::class,
    UserDAO::class
);
$container->setSimple(\App\Service\DigitalItemRegistrationService::class, DigitalItemDAO::class);
$container->setSimple(\App\Service\RankingService::class, UserDAO::class, StatsDAO::class);
$container->setSimple(FileService::class);

return [$container, $config];
