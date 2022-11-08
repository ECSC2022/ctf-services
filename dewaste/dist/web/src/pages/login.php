<?php

$email ??= "";
$message ??= "";
?>

<?= $message ?>
<form method="post">
    <div class="form-group">
        <label for="email" class="form-label">E-Mail:</label>
        <input class="form-control" type="text" name="email" id="email"
               value="<?= htmlspecialchars($email, ENT_QUOTES) ?>"/>
    </div>
    <div class="form-group">
        <label for="password" class="form-label">Password:</label>
        <input class="form-control" type="password" name="password" id="password"/>
    </div>
    <button class="button">Login</button>
</form>
