<?php

use App\Routes;

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title><?= PLANT_NAME ?> recycling plant<?= isset($title) ? " | " . htmlspecialchars($title) : "" ?></title>
    <link rel="stylesheet" href="/vendor/twbs/bootstrap/dist/css/bootstrap.min.css"/>
    <script defer src="/vendor/twbs/bootstrap/dist/js/bootstrap.min.js"></script>
    <link rel="stylesheet" href="/vendor/fortawesome/font-awesome/css/all.css"/>
    <script defer src="/vendor/fortawesome/font-awesome/js/all.js"></script>
    <link rel="stylesheet" href="/css/style.css"/>
    <script defer src="/js/script.js"></script>
</head>
<body>
<nav class="navbar navbar-expand-lg navbar-dark">
    <div class="container-fluid">
        <a class="navbar-brand" href="/"><?= PLANT_NAME ?></a>
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarSupportedContent"
                aria-controls="navbarSupportedContent" aria-expanded="false" aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarSupportedContent">
            <ul class="navbar-nav me-auto mb-2 mb-lg-0">
                <li class="nav-item"><a class="nav-link" href="<?= Routes::INDEX ?>">Home</a></li>
                <li class="nav-item">
                    <a class="nav-link" href="<?= Routes::RECYCLE_PHYSICAL_REGISTER ?>">Recycle</a>
                </li>
                <li class="nav-item"><a class="nav-link" href="<?= Routes::ANALYZE ?>">Analyze</a></li>
                <li class="nav-item"><a class="nav-link" href="<?= Routes::RANKING ?>">Ranking</a></li>
                <li class="nav-item"><a class="nav-link" href="<?= Routes::FAQ ?>">FAQ</a></li>
                <li class="nav-item"><a class="nav-link" href="<?= Routes::ABOUT ?>">About</a></li>
            </ul>

            <ul class="navbar-nav ms-auto mb-2 mb-lg-0">
                <?php
                if (isset($user)) {
                    ?>
                    <span class="navbar-text">Welcome, <?= htmlspecialchars($user->getFullname()) ?> | </span>
                    <li class="nav-item"><a class="nav-link" href="<?= Routes::RECYCLE_MYITEMS ?>">My Items</a></li>
                    <li class="nav-item"><a class="nav-link" href="<?= Routes::USER_LOGOUT ?>">Logout</a></li>
                    <?php
                } else {
                    ?>
                    <li class="nav-item"><a class="nav-link" href="<?= Routes::USER_LOGIN ?>">Login</a></li>
                    <?php
                }
                ?>
            </ul>
        </div>
    </div>
</nav>

<header class="container">
    <h1><?= PLANT_NAME ?></h1>
    <p class="slogan"></p>
</header>

<main class="container">
    <?= $content ?? "" ?>
</main>

<footer class="container">
    <div class="d-flex align-items-center">
        <p class="flex-grow-1">
            No sensible decision can be made any longer without taking into account not only the world
            as it is, but the world as it will be.
            <br>
            <i>&mdash; Isaac Asimov</i>
        </p>
        <div>
            <a class="button m-0" href="<?= REPORT_APP_URL ?>">Report issue</a>
        </div>
    </div>
</footer>
</body>
</html>