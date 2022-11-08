<?php

namespace App\Controllers;

use App\Model\Redirection;
use App\Model\Route;
use App\Routes;
use App\Service\SessionService;
use App\Service\UserLoginService;
use App\UI\Template;

class UserController
{
    public function __construct(
        private readonly Template $template,
        private readonly UserLoginService $userLoginService,
        private readonly SessionService $sessionService,
    ) {
    }

    #[Route(Routes::USER_LOGIN, [Route::GET, Route::POST])]
    public function login(): string
    {
        $email = "";
        $msg = "";

        if (isPostRequest()) {
            $email = parsePostString("email") ?? "";
            $password = parsePostString("password") ?? "";

            $user = $this->userLoginService->login($email, $password);
            if ($user === null) {
                $msg = errorBox("Invalid email or password.");
            } else {
                throw new Redirection(Routes::RECYCLE_MYITEMS);
            }
        }

        $loginPage = $this->template->dynamicTemplate("login.php", email: $email, message: $msg);
        return $this->template->withMainLayout("Login", $loginPage);
    }

    #[Route(Routes::USER_LOGOUT)]
    public function logout(): string
    {
        $this->sessionService->setUser(null);
        throw new Redirection(Routes::USER_LOGIN);
    }
}
