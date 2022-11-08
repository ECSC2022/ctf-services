<?php

namespace App\Persistence;

use App\Model\DuplicateEmailAddressException;
use App\Model\User;
use PDOException;

class UserDAO
{
    public function __construct(private readonly \PDO $db)
    {
    }

    /**
     * @param array{id:int,email:string,firstname:string,lastname:string} $row
     * @return User
     */
    private function parseRow(array $row): User
    {
        $u = new User();
        $u->id = $row["id"];
        $u->email = $row["email"];
        $u->firstname = $row["firstname"];
        $u->lastname = $row["lastname"];
        return $u;
    }

    public function getByEmailAndPassword(string $email, string $password): ?User
    {
        $stmt = $this->db->prepare("SELECT * FROM users WHERE email = e? AND password = sha512(e?) LIMIT 1");
        $stmt->execute([$email, $password]);
        if ($stmt->rowCount() === 0) {
            return null;
        }
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);
        return $this->parseRow($row);
    }

    /**
     * @param User $user
     * @param string $newPassword
     * @return void
     * @throws DuplicateEmailAddressException
     */
    public function create(User $user, string $newPassword): void
    {
        try {
            $stmt = $this->db->prepare(<<<SQL
INSERT INTO users 
    (email, password, firstname, lastname) 
VALUES 
    (e?,sha512(e?),e?,e?)
SQL
            );
            $stmt->execute([$user->email, $newPassword, $user->firstname, $user->lastname]);
            $user->id = (int) $this->db->lastInsertId();
        } catch (PDOException $e) {
            if ($e->errorInfo !== null && $e->errorInfo[0] === "23505" && str_contains($e->errorInfo[2], "email")) {
                throw new DuplicateEmailAddressException("Email $user->email already exists.", $e);
            }
            throw $e;
        }
    }

    public function getByEmail(string $email): ?User
    {
        $stmt = $this->db->prepare("SELECT * FROM users WHERE email = e?");
        $stmt->execute([$email]);
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);
        if ($row === null) {
            return null;
        }
        return $this->parseRow($row);
    }

    public function getById(int $userId): ?User
    {
        $stmt = $this->db->prepare("SELECT * FROM users WHERE id = ?");
        $stmt->execute([$userId]);
        $row = $stmt->fetch(\PDO::FETCH_ASSOC);
        if ($row === null) {
            return null;
        }
        return $this->parseRow($row);
    }

    /**
     * @return array<User>
     */
    public function getAll(): array
    {
        $stmt = $this->db->query("SELECT * FROM users");
        assert($stmt !== false, "PDO in wrong error mode (Exception expected)");
        $ret = [];
        while ($row = $stmt->fetch(\PDO::FETCH_ASSOC)) {
            $u = $this->parseRow($row);
            $ret[$u->id] = $u;
        }
        return $ret;
    }
}
