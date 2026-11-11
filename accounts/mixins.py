from accounts.permissions import user_has_role


class SocietyScopeMixin:

    def filter_by_society_scope(self, queryset, society_field="society"):
        user = self.request.user

        # Department Officers can view all societies.
        if user_has_role(user, "Department Officer"):
            return queryset

        # Society Admin and Secretary can access
        # records belonging to their assigned societies.
        if (
            user_has_role(user, "Society Admin")
            or user_has_role(user, "Society Secretary")
        ):
            society_ids = user.role_assignments.filter(
                role__name__in=[
                    "Society Admin",
                    "Society Secretary",
                ],
                society__isnull=False,
            ).values_list("society_id", flat=True)

            return queryset.filter(
                **{f"{society_field}__in": society_ids}
            )

        return queryset.none()

    def filter_by_board_scope(self, queryset, board_field="board"):
        user = self.request.user

        if not user_has_role(user, "Board User"):
            return queryset.none()

        board_ids = user.role_assignments.filter(
            role__name="Board User",
            board__isnull=False,
        ).values_list("board_id", flat=True)

        return queryset.filter(
            **{f"{board_field}__in": board_ids}
        )

    def filter_by_department_office_scope(
        self,
        queryset,
        office_field="department_office",
    ):
        user = self.request.user

        office_ids = user.role_assignments.filter(
            role__name="Department Officer",
            department_office__isnull=False,
        ).values_list("department_office_id", flat=True)

        return queryset.filter(
            **{f"{office_field}__in": office_ids}
        )