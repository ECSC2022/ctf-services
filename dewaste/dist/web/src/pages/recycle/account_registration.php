<?php

use App\Model\User;

$_ = fn(string $unsafe) => htmlspecialchars($unsafe, ENT_QUOTES);
$checkedIf = fn(bool $x) => $x ? "checked" : "";

/** @var string|null $userType */
$userType ??= "account";
/** @var bool|null $loggedIn */
$loggedIn ??= false;
/** @var string|null $loginEmail */
$loginEmail ??= "";
/** @var User|null $user */
$user ??= null;

$userVal = fn(string $name): string => $_($user?->$name ?? "");

if ($loggedIn) {
    return;
}
?>
<fieldset>
    <h4>User information</h4>

    <div class="row">
        <div class="col">
            <p>
                If you want to see the current processing status of your item, you need to register
                an account. We use this data only to authenticate you and to send you notifications 
                about the status of your submitted items.
            </p>
        </div>
        <div class="col">
            <div class="form-check">
                <input type="radio" name="auth_type" id="auth_type_account" value="account"
                       class="form-check-input" <?= $checkedIf($userType === "account") ?>
                       data-only-show-when-active="#user-authentication-form"/>
                <label for="auth_type_account" class="form-check-label">
                    I want to <strong>register</strong> an account or use and already <strong>existing
                    one</strong>.
                </label>
            </div>
            <div class="form-check">
                <input type="radio" name="auth_type" id="auth_type_once" value="once"
                       class="form-check-input" <?= $checkedIf($userType === "once") ?> />
                <label for="auth_type_once" class="form-check-label">
                    I do not want to register an account. I will get a link once which can be used 
                    to track my order.
                </label>
            </div>
        </div>
    </div>

    <div id="user-authentication-form" class="row gx-5 hideable">
        <div class="col new-user-form">
            <h5>New user</h5>
            <p>
                Register a new account.
            </p>
            <div class="form-group">
                <label for="newEmail" class="form-label">E-Mail</label>
                <input type="email" id="newEmail" name="newEmail" value="<?= $userVal("email") ?>"
                       class="form-control"/>
            </div>
            <div class="form-group">
                <label for="newPassword" class="form-label">Password</label>
                <input type="password" id="newPassword" name="newPassword" class="form-control"/>
            </div>
            <div class="row">
                <div class="col">
                    <div class="form-group">
                        <label for="newFirstname" class="form-label">Firstname</label>
                        <input type="text" id="newFirstname" name="newFirstname"
                               value="<?= $userVal("firstname") ?>"
                               class="form-control"/>
                    </div>
                </div>
                <div class="col">
                    <div class="form-group">
                        <label for="newLastname" class="form-label">Lastname</label>
                        <input type="text" id="newLastname" name="newLastname"
                               value="<?= $userVal("lastname") ?>"
                               class="form-control"/>
                    </div>
                </div>
            </div>
        </div>
        <div class="col">
            <h5>Existing user</h5>
            <p>
                Register with your existing credentials.
            </p>
            <div class="form-group">
                <label for="email" class="form-label">E-Mail</label>
                <input type="email" id="email" name="email" value="<?= $_($loginEmail) ?>"
                       class="form-control"/>
            </div>
            <div class="form-group">
                <label for="password" class="form-label">Password</label>
                <input type="password" id="password" name="password" class="form-control"/>
            </div>
        </div>
    </div>
</fieldset>